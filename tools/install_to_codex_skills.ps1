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
$targetSkills = Join-Path $CodexHome "skills"

New-Item -ItemType Directory -Path $targetSkills -Force | Out-Null

foreach ($name in $Skill) {
    $source = Join-Path $repoSkills $name
    $destination = Join-Path $targetSkills $name

    if (-not (Test-Path -LiteralPath $source)) {
        throw "Skill not found in repo: $source"
    }

    if ($Clean -and (Test-Path -LiteralPath $destination)) {
        $resolved = Resolve-Path -LiteralPath $destination
        if (-not $resolved.Path.StartsWith((Resolve-Path -LiteralPath $targetSkills).Path)) {
            throw "Refusing to remove unexpected path: $($resolved.Path)"
        }
        Remove-Item -LiteralPath $resolved.Path -Recurse -Force
    }

    Copy-Item -LiteralPath $source -Destination $targetSkills -Recurse -Force
    Write-Host "Installed $name"
}

