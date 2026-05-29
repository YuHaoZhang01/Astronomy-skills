param(
    [string[]]$Skill = @(
        "astrophysics-paper-data-finder",
        "hatch-pet",
        "sn-lightcurve-plot-style"
    ),
    [string]$CodexHome = "$env:USERPROFILE\.codex",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$repoSkills = Join-Path $repoRoot "skills"
$sourceSkills = Join-Path $CodexHome "skills"

New-Item -ItemType Directory -Path $repoSkills -Force | Out-Null

foreach ($name in $Skill) {
    $source = Join-Path $sourceSkills $name
    $destination = Join-Path $repoSkills $name

    if (-not (Test-Path -LiteralPath $source)) {
        throw "Skill not found: $source"
    }

    if ($Clean -and (Test-Path -LiteralPath $destination)) {
        $resolved = Resolve-Path -LiteralPath $destination
        if (-not $resolved.Path.StartsWith((Resolve-Path -LiteralPath $repoSkills).Path)) {
            throw "Refusing to remove unexpected path: $($resolved.Path)"
        }
        Remove-Item -LiteralPath $resolved.Path -Recurse -Force
    }

    Copy-Item -LiteralPath $source -Destination $repoSkills -Recurse -Force
    Write-Host "Synced $name"
}

