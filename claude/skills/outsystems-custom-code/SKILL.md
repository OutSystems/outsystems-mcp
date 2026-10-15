---
name: outsystems-custom-code
description: '[Beta] Reference + workflow for building, testing, and deploying C# class-library "External Logic" libraries for OutSystems Developer Cloud (ODC). Covers SDK attributes ([OSInterface] / [OSAction] / [OSParameter] / [OSStructure] / [OSIgnore]), supported data types, optional parameters, logging via ILogger, project structure, runtime constraints (95s execution / 1 GB memory / 5.5 MB payload), unit + container integration tests, and deployment via the OutSystems MCP. Use when the user asks to "build a C# library for OutSystems", "create ODC external logic", "write custom code for ODC", "deploy an external library", "publish C# code to OutSystems", or names ODC External Logic / external library / OSInterface / OSAction directly.'
license: MIT
compatibility: Ships for Claude Code, Cursor and Kiro. Needs a shell with the .NET 10 SDK, and Docker for the integration tests, so Claude Desktop's Chat tab, which has no shell, can't run it. Deployment requires the `outsystems` MCP server connected and authenticated, and builds on the main `outsystems` skill for the upload, polling and publish rules. Python is NOT required by this skill.
metadata:
  version: "1.3.0"
  author: outsystems-r-and-d
  maturity: beta
---

**Beta Feature.** This skill is a Beta Feature: a non-final OutSystems capability provided to collect customer feedback. It can change significantly, including through breaking changes, or be discontinued. The first time you use this skill in a conversation, tell the user it's a Beta Feature and share <https://www.outsystems.com/legal/beta-features-agreement>.

# OutSystems ODC External Library Skill

This file describes how to create, build, test, and deploy C# libraries for the OutSystems Developer Cloud (ODC) External Logic feature.

**Load the main `outsystems` skill before uploading: upload, polling and publish rules come from it** (read the live tool catalog, poll long-running operations to terminal, confirm before every tenant write). The main skill's upload, polling and publish rules apply, and this skill's two confirmations (see [Upload and publish](#upload-and-publish)) always apply on top of them. For building and packaging the library, follow this skill.

---

## Project Overview

OutSystems ODC External Logic allows extending ODC apps with custom C# code. The C# class library project is built locally, published as a ZIP file to the ODC platform. OutSystems generates a wrapper around the code that exposes the decorated interfaces as server actions consumable by ODC applications.

---

## Runtime Constraints

These are hard limits enforced by the ODC platform. Never design functions that approach or exceed them:

| Constraint | Limit |
|---|---|
| Max execution duration | **95 seconds** per function call |
| Max memory | **1,024 MB** |
| Max ephemeral storage | **512 MB** |
| Max payload (inputs + outputs combined) | **5.5 MB** |

For large data: stream in chunks, use references/URLs instead of raw bytes.

---

## Project Setup

### Target Framework
- Use **.NET 10**. Do **not** use .NET 6 or .NET 8: .NET 8 support is ending, and after that ODC
  refuses to upload, update, or install a library that targets it.
- Project type: **Class Library** (`<OutputType>Library</OutputType>`).
- If the project targets an older .NET, update it to .NET 10.

### Before you build
If `dotnet --list-sdks` shows no 10.x SDK, or `docker info` fails, tell the user and stop at the
step that needs it: the build and unit tests need the SDK, the container tests need Docker.

### Required NuGet Package
```xml
<PackageReference Include="OutSystems.ExternalLibraries.SDK" Version="1.7.0" />
```
Always use the latest stable version. Check: https://www.nuget.org/packages/OutSystems.ExternalLibraries.SDK

### Minimal `.csproj`
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="OutSystems.ExternalLibraries.SDK" Version="1.7.0" />
  </ItemGroup>
</Project>
```

Note: the SDK package itself may only ship `net8.0`/`netstandard2.0` assets (no `net10.0`-specific
build) — that's fine, NuGet resolves the closest compatible asset and it runs correctly under a
`net10.0`-targeted project.

---

## SDK Attributes – Core Concepts

### `[OSInterface]` – Exposes the interface to ODC
Applied to a **public interface**. Every method on this interface becomes a server action in ODC.

```csharp
using OutSystems.ExternalLibraries.SDK;

namespace MyCompany.MyLibrary
{
    [OSInterface(
        Name = "MyLibrary",
        Description = "Short description of what this library does."
    )]
    public interface IMyLibrary
    {
        [OSAction(Description = "Greets a person by name")]
        string Greet(
            [OSParameter(Description = "Name to greet")] string name
        );
    }
}
```

- `Name`: The library name in ODC. It also decides whether an upload creates a new library or a new revision, so always set it. Required for ODC Forge submission.
- `Description`: Shown in ODC Portal. Required for Forge submission.
- `IconResourceName`: the embedded resource name of the library's PNG icon. Required for Forge submission. Add the icon to the project as an `EmbeddedResource` item and set `<RootNamespace>MyCompany.MyLibrary</RootNamespace>` in the `.csproj`; the resource name is then the root namespace, the folder and the file name, joined with dots (for an icon in `Resources`, `MyCompany.MyLibrary.Resources.` followed by the file name). Keep these out of the minimal `.csproj`: the build fails when the icon file doesn't exist.

### `[OSAction]` – Customise action metadata (optional)
Applied to individual interface methods to override defaults.

```csharp
[OSAction(
    Description = "Validates an IBAN and returns structured result.",
    ReturnName = "ValidationResult",
    ReturnDescription = "The validation outcome."
)]
ValidationResult ValidateIban(string iban);   // ValidationResult: an [OSStructure] struct, defined elsewhere
```

### `[OSParameter]` – Customise parameter metadata (optional)
```csharp
void ProcessData(
    [OSParameter(Description = "Raw input bytes", DataType = OSDataType.BinaryData)]
    byte[] data,
    [OSParameter(Description = "Output result")]
    out string result
);
```

### Optional Parameters

To make a server action parameter optional in ODC, the C# parameter **must** be both nullable **and** have a default value of `null`.

```csharp
// In interface:
[OSAction(Description = "Sends a notification")]
void SendNotification(
    [OSParameter(Description = "Recipient address")] string recipient,
    [OSParameter(Description = "Optional message subject")] string? subject = null,
    [OSParameter(Description = "Optional priority level")] int? priority = null
);

// In implementation:
public void SendNotification(string recipient, string? subject = null, int? priority = null)
{
    var resolvedSubject = subject ?? "No Subject";
    var resolvedPriority = priority ?? 0;
    // ...
}
```

**Rules to make parameter optional:**
- The parameter type must be nullable: `string?`, `int?`, `bool?`, `decimal?`, etc.
- The parameter must have `= null` as the default value in both the interface and the implementation.
- `byte[]?` (Binary Data) and struct types decorated with `[OSStructure]` can also be made optional the same way.
- `out` parameters cannot be optional.

### `[OSStructure]` – Exposes a struct as an ODC Structure
Applied to a **public struct** (not class). Used for complex input/output types.

```csharp
[OSStructure(Description = "Represents a parsed IBAN value.")]
public struct IbanResult
{
    [OSStructureField(Description = "Two-letter country code", IsMandatory = true)]
    public string Country { get; set; }

    [OSStructureField(Description = "Basic Bank Account Number")]
    public string Bban { get; set; }

    [OSStructureField(Description = "Whether the IBAN is valid")]
    public bool IsValid { get; set; }
}
```

### `[OSIgnore]` – Hides a member from ODC
Apply to methods or properties that should not be exposed as actions or structure fields.

### `OriginalName` – on every decorated element (optional)
`[OSInterface]`, `[OSAction]`, `[OSParameter]`, `[OSStructure]` and `[OSStructureField]` all accept an
`OriginalName` property. It holds the original name, so the key ODC calculates stays the same when you
rename the namespace, interface, method, parameter or struct, and the apps that use the library keep
working. On `[OSInterface]` it's the previous namespace plus the previous library name.

```csharp
[OSInterface(Name = "MyLibrary", OriginalName = "MyCompany.MyLibrary.MyLibrary")]
```

---

## Logging
To log from your custom code, including informational messages and errors, use the Microsoft.Extensions.Logging ILogger interface in your C# code. Only Information and higher levels show in the ODC Portal logs. The library class receives the `ILogger` in its constructor. The OutSystems SDK package doesn't bring it, so add the `Microsoft.Extensions.Logging.Abstractions` package (`<PackageReference Include="Microsoft.Extensions.Logging.Abstractions" Version="10.0.12" />`): it holds `ILogger`, `LogInformation` and `NullLogger`, which is all a library needs, because ODC creates the logger and passes it in. It adds about 60 KB of Microsoft DLLs to the upload ZIP, so add it only when the library logs. The ODC SDK README names the full `Microsoft.Extensions.Logging` package, which also works: it depends on this one and adds about 120 KB more for creating loggers, which a library doesn't do.

The logging version of the `MyLibrary` class from the [Implementation Pattern](#implementation-pattern):

```csharp
using Microsoft.Extensions.Logging;
using System.Diagnostics;

namespace MyCompany.MyLibrary
{
    public class MyLibrary : IMyLibrary
    {
        private readonly ILogger _logger;

        public MyLibrary(ILogger logger)
        {
            _logger = logger;
        }

        public string Greet(string name)
        {
            using var activity = Activity.Current?.Source.StartActivity("MyLibrary.Greet");
            _logger.LogInformation($"Greeting {name}");
            return $"Hello, {name}!";
        }
    }
}
```

A library that logs takes the logger in its constructor, so its tests pass `NullLogger.Instance`
(`using Microsoft.Extensions.Logging.Abstractions;`): `new MyLibrary(NullLogger.Instance)`.

---

## Supported Data Types

Only these types are valid as method parameters and return types:

| C# Type | ODC Type |
|---|---|
| `string` | Text |
| `int` | Integer |
| `long` | Long Integer |
| `bool` | Boolean |
| `decimal` | Decimal |
| `float` | Decimal |
| `double` | Decimal |
| `DateTime` | DateTime |
| `byte[]` | Binary Data |
| struct with `[OSStructure]` | Structure |
| `IEnumerable<T>` of any above | List |

**Not supported:** classes, dictionaries, enums (wrap in int/string), generics other than
`IEnumerable`/`out` — **including `Task` and `Task<T>`**.

Nullable forms of the supported value types (`int?`, `bool?`, `decimal?`, …) ARE valid, but only
as the optional-parameter form described under [Optional Parameters](#optional-parameters) — a
nullable type with an `= null` default. Do not use one as a return type or a structure field.

### No async signatures on `[OSInterface]` methods
`OSAction` methods must return one of the supported types directly (or `void`) — never `Task` or
`Task<T>`. An interface method declared as `Task<string> function(...)` fails at library-generation
time with:

```
The struct decorated with OSStructure ''Evaluate' return value' contains a public
property/field that uses an unsupported parameter type 'Task`1'. (OS-ELG-MODL-05015)
```

If the implementation needs to call an async API (e.g. an async SDK client), keep the **interface**
method synchronous and block on the async call **inside the implementation**:

```csharp
// Interface — synchronous signature, required by ODC
string Evaluate(string rule, string input);

// Implementation — awaits internally, blocks with GetAwaiter().GetResult()
public string Evaluate(string rule, string input)
{
    var response = SomeAsyncClient.CallAsync(input).GetAwaiter().GetResult();
    return response.ToString();
}
```

This applies even when the sample code for a third-party library you're wrapping is `async`/`await`
end-to-end — adapt it to a synchronous boundary at the `[OSInterface]` method.

---

## Recommended Project Structure

Keep the test projects next to the library project, not inside its folder: a project compiles every
`.cs` file under its own folder, so test code inside `MyLibrary/` would be built into the library.

```
MyLibrary.slnx                 # `dotnet new sln` creates .slnx on the .NET 10 SDK
global.json                    # opts `dotnet test` into Microsoft.Testing.Platform (see Unit Tests)
MyLibrary/
├── MyLibrary.csproj
├── Interfaces/
│   └── IMyLibrary.cs          # [OSInterface]-decorated interface
├── Implementations/
│   └── MyLibrary.cs           # Class implementing the interface
├── Structures/
│   └── MyResult.cs            # [OSStructure]-decorated structs
└── Resources/                 # the PNG icon, as an EmbeddedResource (see IconResourceName)
MyLibrary.UnitTests/
└── MyLibraryTests.cs
MyLibrary.IntegrationTests/
└── ContainerTests.cs
```

---

## Implementation Pattern

The interface and the implementing class must be in the same assembly. ODC finds the implementation via the interface.

```csharp
// Interfaces/IMyLibrary.cs
using OutSystems.ExternalLibraries.SDK;

namespace MyCompany.MyLibrary
{
    [OSInterface(
        Name = "MyLibrary",
        Description = "Short description of what this library does."
    )]
    public interface IMyLibrary
    {
        [OSAction(Description = "Greets a person by name")]
        string Greet(
            [OSParameter(Description = "Name to greet")] string name
        );
    }
}

// Implementations/MyLibrary.cs
namespace MyCompany.MyLibrary
{
    public class MyLibrary : IMyLibrary
    {
        public string Greet(string name) => $"Hello, {name}!";
    }
}
```

### Output Parameters
Use `out` parameters for multiple return values:

```csharp
// In interface (MyResult: an [OSStructure] struct, defined elsewhere):
void Parse(string input, out bool success, out string errorMessage, out MyResult result);

// In implementation:
public void Parse(string input, out bool success, out string errorMessage, out MyResult result)
{
    // ...
}
```

---

## Testing

### Unit Tests
Use standard .NET test frameworks. The library code has no ODC runtime dependency, so it can be tested directly.

```xml
<!-- MyLibrary.UnitTests.csproj — xUnit v3: the test project is an executable -->
<OutputType>Exe</OutputType>

<PackageReference Include="xunit.v3" Version="4.*" />
<PackageReference Include="xunit.runner.visualstudio" Version="4.*" />

<ProjectReference Include="../MyLibrary/MyLibrary.csproj" />
```

xUnit v3 renames the package from `xunit` to `xunit.v3`. The Visual Studio / `dotnet test` runner
keeps its name, `xunit.runner.visualstudio`, but must be 3.0.0 or later; its 4.0.0 was released
alongside `xunit.v3` 4.0.0.

Put the test class in a namespace under the library's, as below: xUnit v3 generates code under the
test project's root namespace (`MyLibrary.UnitTests`), so in the global namespace `MyLibrary` would
resolve to that namespace instead of the class.

```csharp
using Xunit;

namespace MyCompany.MyLibrary.UnitTests
{
    public class MyLibraryTests
    {
        private readonly IMyLibrary _sut = new MyLibrary();

        [Fact]
        public void Greet_ReturnsExpectedString()
        {
            var result = _sut.Greet("World");
            Assert.Equal("Hello, World!", result);
        }
    }
}
```

Run: `dotnet test`

On the .NET 10 SDK, `dotnet test` runs xUnit v3 tests only through Microsoft.Testing.Platform, so
add a `global.json` at the solution root. Without it, `dotnet test` fails with "Testing with VSTest
target is no longer supported by Microsoft.Testing.Platform on .NET 10 SDK and later".

```json
{
  "test": {
    "runner": "Microsoft.Testing.Platform"
  }
}
```

### Integration Tests (Container)
Integration tests should run the code in a container matching the ODC runtime environment.

**Base image:** `mcr.microsoft.com/dotnet/aspnet:10.0` — match the .NET version the library
targets, or the tests validate a runtime the library will never run on.

Set up `MyLibrary.IntegrationTests` like the unit-test project (the same `.csproj`, with `OutputType`
Exe), with its tests in `ContainerTests.cs`.

Example `Dockerfile` for integration tests, at the solution root:
```dockerfile
FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS base

FROM --platform=$BUILDPLATFORM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY . .
RUN dotnet publish MyLibrary.IntegrationTests/MyLibrary.IntegrationTests.csproj -c Release -o /app/publish

FROM base AS final
WORKDIR /app
COPY --from=build /app/publish .
ENTRYPOINT ["dotnet", "MyLibrary.IntegrationTests.dll"]
```

Add a `.dockerignore` next to it, so the host's build outputs aren't copied into the image:
```
**/bin/
**/obj/
```

The runtime image has no SDK, so `dotnet test` and `dotnet vstest` are not available in it. An
xUnit v3 test project is an executable (`<OutputType>Exe</OutputType>`, as in the unit tests), so
running its `.dll` runs the tests and exits non-zero when one fails.

The `dotnet publish` in this Dockerfile builds the **integration-test project** for the test container.
It is not the upload artifact — for that, see [Package](#package).

Run integration tests:
```bash
docker build --platform linux/amd64 -t mylibrary-integration-tests .
docker run --rm --platform linux/amd64 --memory=1g --memory-swap=1g mylibrary-integration-tests
```

ODC runs linux-x64, so `--platform linux/amd64` runs the tests on that platform, also on an Apple
Silicon Mac. The build stage stays on the machine's own platform (`--platform=$BUILDPLATFORM`),
because the SDK build crashes under emulation. `--memory=1g --memory-swap=1g` applies the 1 GB limit.
Docker can't enforce the 512 MB storage or the 95-second limit, so the tests measure those themselves.

**What to validate in integration tests:**
- All public actions execute without exceptions in the target runtime
- Memory usage stays within 1,024 MB for expected payloads
- Execution completes within 95 seconds
- Payload sizes (serialised inputs + outputs) stay under 5.5 MB

### Live-Tenant Smoke Tests (optional third tier)
For a library other apps will depend on, add smoke tests that call the published library through a real ODC app.
See the `UltimatePDF_ExternalLogic.E2ETests` project in the primary [worked example](#worked-examples).

---

## Package

Publish the **library project** (not a test project) for the Linux x64 runtime ODC runs it on:

```bash
dotnet publish MyLibrary/MyLibrary.csproj -c Release -r linux-x64 --self-contained false
```

Then zip the *contents* of `MyLibrary/bin/Release/net10.0/linux-x64/publish/` to the root of the ZIP.
That ZIP is what you upload.

- macOS or Linux: `cd MyLibrary/bin/Release/net10.0/linux-x64/publish && zip -r ../MyLibrary.zip .`
- Windows (PowerShell): `Compress-Archive -Path MyLibrary\bin\Release\net10.0\linux-x64\publish\* -DestinationPath MyLibrary.zip`

The ODC docs also give a portable form without `-r linux-x64`; the runtime-specific form above is
the one they require when the library has runtime-specific dependencies. It is also the form
OutSystems' own public external-library repositories use (see [Worked Examples](#worked-examples)).
`--no-self-contained` is the same flag as `--self-contained false`.

---

## Upload and publish

Upload and publish with the main `outsystems` skill's "Publish a new external library" flow: upload the ZIP, poll until the library is ready for review (pull the operation logs on a validation failure), publish it, and poll until it is published. If the `outsystems` MCP server isn't connected, follow the main skill's setup for your harness.

The upload sends the ZIP inside the request as base64 text, so keep it small: add only the packages the library uses.

Before the upload, run `dotnet test` and the container tests, and upload only when they pass.

- **Uploading and publishing are tenant writes: confirm each one.** Before the upload, look up the tenant's external libraries (a read-only listing) for one with the same `[OSInterface]` `Name`. A name match is only a hint: the library key comes from the interface's namespace plus `Name` (or `OriginalName`). Restate the upload ("upload the external library MyLibrary from MyLibrary.zip") and say whether it looks like a new library or a new revision of the existing one, with that library's key, or that you can't tell; don't guess. Wait for explicit confirmation. After the upload, the status gives the library key: compare it with the existing library's key. Before the publish, restate it ("publish the external library MyLibrary"), say whether it is a new library or a new revision, and wait again. Don't offer to approve them in advance. These two confirmations always apply, even when the user asked for the upload or the publish in the same request.
- If the user declines the publish, the uploaded library stays unpublished; tell them, with the operation key.
- To use the library in an app, follow the main skill's "Reference an external library from an app". The app's publish is a tenant write too and gets its own confirmation.
- To move the published library to another stage, use the main skill's promotion flow. An external library has no impact analysis, so tell the user before you ask them to confirm.

---

## Worked Examples

Public OutSystems repositories to read end to end. Read the code; where a repository's prose docs
disagree with its code, trust the code.

- **Primary — [OutSystems/UltimatePDF-ExternalLogic](https://github.com/OutSystems/UltimatePDF-ExternalLogic)**
  (BSD-3-Clause). A complete, shipping library: `src/UltimatePDF_ExternalLogic/IUltimatePDF_ExternalLogic.cs`
  (the `[OSInterface]` / `[OSAction]` surface, with optional nullable `[OSStructure]` parameters),
  `src/UltimatePDF_ExternalLogic/UltimatePDF_ExternalLogic.csproj` (`net10.0`), the unit, integration
  and live-tenant E2E test projects under `src/`, and `generate_upload_package.ps1` (publish + zip). Read these scripts; do not run them: they change the
  user's PowerShell execution policy.
- **Secondary, minimal — [OutSystems/vanguard-xml-to-json](https://github.com/OutSystems/vanguard-xml-to-json)**
  (MIT). One interface, one action, one structure: the smallest complete example
  (`XmlToJson/IXmlToJson.cs`, `XmlToJson/XmlToJson.csproj`, `XmlToJson/generate_upload_package.ps1`, which also changes the execution policy: read it, don't run it).
  Its README states *"THIS CODE IS NOT SUPPORTED BY OUTSYSTEMS"* — read it as a minimal SDK sample,
  not as supported OutSystems practice.

---

## Common Errors & Fixes

| Error | Cause | Fix |
|---|---|---|
| Interface not found | Implementing class not in same assembly | Ensure interface and class are in the same `.csproj` |
| Unsupported type | Using `class` instead of `struct` for complex types | Use `struct` with `[OSStructure]` |
| ZIP structure wrong | Folder nested inside ZIP | Zip the *contents* of `/publish`, not the folder itself |
| Payload too large | Input/output exceeds 5.5 MB | Chunk data, use URLs, or split into multiple actions |
| `Server is busy, retry shortly` on upload | All upload slots on the server were busy | Transient when it arrives as a `CapacityError`, or as a `ValidationError` from older servers: retry with backoff, as the main `outsystems` skill describes |
| Timeout | Single action takes more than 95 seconds | Break up long-running work; split the work across several actions |
| Missing icon | Forge submission fails | Embed PNG as `EmbeddedResource` and set `IconResourceName` |
