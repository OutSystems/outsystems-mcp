# App Spec: <APP_NAME>

> Fill in every section. Empty sections cause Mentor to confabulate.
> The spec validator (`build.py validate-spec`) enforces that
> sections 1, 2, 3, 4, and 8 are present and non-trivial.

## 1. Overview

**Purpose:** <one paragraph — what does this app do, who uses it, what value does it deliver?>

**Target users:** <which roles or human-job-titles use this app>

**App shell key:** <asset key — created in ODC Portal first; Mentor edits this shell, doesn't create it>

**Style direction:** <Apply OutSystems UI defaults / Reference existing app for theme: <app_name> / Custom theme (provide specs)>

---

## 2. Roles

List every distinct role. For each role, name + 1-line description of what they can do.

- **Role A**: <description>
- **Role B**: <description>
- **Anonymous**: (only list if anonymous access is intentional — e.g. for public-facing login screens)

---

## 3. Data model

### Entities

| Entity | Attributes (name, type, constraint) | Relationships |
|---|---|---|
| <EntityName> | <e.g. Id (Long Integer, mandatory), Name (Text, max 100, mandatory), Email (Email, max 256, mandatory), CreatedAt (Date Time, mandatory)> | <e.g. FK to OtherEntity via OtherEntityId> |

### Static enums

| Enum | Values |
|---|---|
| <EnumName> | <Value1, Value2, Value3> |

---

## 4. Screens + RBAC

> Critical for preventing Mentor's known RBAC fumble. Every row must
> have an explicit role list — even if it's just "All authenticated".
> Do NOT leave the role column blank.

| Screen | Purpose | Accessible by (roles) |
|---|---|---|
| <ScreenName> | <one-line purpose> | <comma-separated roles, or "Anonymous", or "All authenticated"> |

---

## 5. Server actions (optional but recommended)

If you know the actions you want, list them. If you leave this empty,
Mentor will derive actions from the screens — but the explicit list
gives you better control.

- **<ActionName>(<input1: Type>, <input2: Type>)** → returns `<OutputType>`. <one-line purpose>

---

## 6. Integrations (optional)

External APIs, AI model connections, REST endpoints, libraries this
app needs to reference.

- **<Integration name>**: <type — REST / SOAP / AI Model Connection / Library> — <one-line purpose>

If "none", explicitly state "None" — don't leave the section empty.

---

## 7. UI/UX direction (optional)

- Theme: <`OutSystems UI defaults` / `Reference: <app_name>`>
- Layout style: <`Dashboard with sidebar nav` / `Top-nav with breadcrumbs` / `Form-only`>
- Mobile-responsive: <`Yes` / `Desktop-only`>
- Branding constraints: <e.g. "Customer's blue (#3A4168) primary color">

---

## 8. Out of scope

> Critical for stopping Mentor from over-building. List things you
> explicitly DON'T want. Mentor respects these.

- <e.g. "Public REST endpoints — internal-only for now">
- <e.g. "Multi-tenant data isolation — single-tenant only">
- <e.g. "Audit log UI — server-side logging only, no admin screen">

---

## 9. Acceptance criteria (optional)

How will you know this build succeeded?

- <e.g. "User can log in as Manager and see all orders, including those they didn't create">
- <e.g. "Database has at least 5 example orders seeded">
- <e.g. "Dashboard shows correct count of orders by status">

---

## 10. Notes for Mentor (optional)

Anything special Mentor should know. Examples:

- "This app will integrate with FlightControl later — keep the data model compatible with their schema."
- "Customer prefers green colors over blue."
- "The OutSystemsUI defaults are fine."
- "Skip the seed data action — we'll use BootstrapData manually."
