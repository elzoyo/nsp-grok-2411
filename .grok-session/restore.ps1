$ErrorActionPreference = "Stop"
$id = "01a06e01-5cac-7511-bc2a-a0dd4373fd76"
$here = $PSScriptRoot
$src = Join-Path $here $id
$repo = (Resolve-Path (Join-Path $here "..")).Path
$enc = [uri]::EscapeDataString($repo)
$dstDir = Join-Path $env:USERPROFILE ".grok\sessions\$enc"
$dst = Join-Path $dstDir $id
if (-not (Test-Path $src)) { throw "No esta el snapshot: $src" }
New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
robocopy $src $dst /E /R:1 /W:1 | Out-Null
Write-Host "Sesion copiada a $dst"
Write-Host "Desde el repo: grok --resume $id"
