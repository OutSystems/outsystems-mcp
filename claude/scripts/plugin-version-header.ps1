# headersHelper of .mcp.json where sh fails: the same output as plugin-version-header.sh.
$manifest = Join-Path $PSScriptRoot '..\.claude-plugin\plugin.json'
$text = Get-Content -Raw -LiteralPath $manifest
if (-not $text -or -not $text.TrimStart().StartsWith('{')) { exit 1 }
$version = ($text | ConvertFrom-Json).version
if (-not ($version -is [string]) -or $version -cnotmatch '\A[0-9A-Za-z.+-]+\z') { exit 1 }
@{ 'X-OutSystems-Plugin-Version' = $version } | ConvertTo-Json -Compress
