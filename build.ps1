# Build the NLmCED images on Windows (PowerShell), from the repository root.
#   .\build.ps1 xnat
#   .\build.ps1 eucaim
param([Parameter(Mandatory=$true)][ValidateSet("xnat","eucaim")][string]$Target)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Version = (Select-String -Path src/nlmced.py -Pattern '^TOOL_VERSION = "(.+)"').Matches[0].Groups[1].Value

if ($Target -eq "xnat") {
    $Base = if ($env:MCR_BASE) { $env:MCR_BASE } else { "mcr-riciannoiselevel:r2024b" }
    docker image inspect $Base *> $null
    if ($LASTEXITCODE -ne 0) { Write-Error "Shared MATLAB Runtime base '$Base' not found on this machine" }
    Write-Host "=== Building nlmced-xnat:$Version on $Base ==="
    docker build -f xnat/Dockerfile --build-arg MCR_BASE=$Base -t "nlmced-xnat:$Version" .
} else {
    Write-Host "=== Building nlmced:$Version (self-contained) ==="
    docker build -f eucaim/Dockerfile -t "nlmced:$Version" .
}
if ($LASTEXITCODE -ne 0) { Write-Error "Build failed" }
Write-Host "=== Done ==="
