<#
.SYNOPSIS
  Собирает MAN-Setup.exe: встраивает скилл в установщик и компилирует C# через csc из .NET Framework.

.EXAMPLE
  .\build.ps1

.EXAMPLE
  .\build.ps1 -Test
#>
param(
  [string]$OutDir,
  [switch]$KeepTemp,
  [switch]$Test
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$skill = Join-Path $root "skills\anti-neuroslop"
if (-not (Test-Path (Join-Path $skill "SKILL.md"))) { throw "Не найден скилл: $skill" }

if (-not $OutDir) { $OutDir = Join-Path $root "dist" }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$work = Join-Path ([System.IO.Path]::GetTempPath()) ("man-build-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $work | Out-Null

try {
  $payload = Join-Path $work "payload"
  $payloadSkill = Join-Path $payload "anti-neuroslop"
  New-Item -ItemType Directory -Path $payloadSkill -Force | Out-Null
  Copy-Item -Path (Join-Path $skill "*") -Destination $payloadSkill -Recurse -Force
  Remove-Item -Force (Join-Path $payloadSkill ".man.json") -ErrorAction SilentlyContinue

  $zip = Join-Path $work "payload.zip"
  Compress-Archive -Path $payloadSkill -DestinationPath $zip -CompressionLevel Optimal
  Write-Host "→ payload: $((Get-Item $zip).Length) байт"

  $csc = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
  if (-not (Test-Path $csc)) { $csc = Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe" }
  if (-not (Test-Path $csc)) { throw "Не найден csc.exe из .NET Framework 4.x" }

  $out = Join-Path $OutDir "MAN-Setup.exe"
  $source = Join-Path $PSScriptRoot "ManInstaller.cs"

  # Аргументы передаются массивом: так они одинаково разбираются
  # в Windows PowerShell 5.1 и PowerShell 7.
  $cscArgs = @(
    "/nologo"
    "/target:exe"
    "/optimize+"
    "/platform:anycpu"
    "/out:$out"
    "/resource:$zip,MAN.payload.zip"
    "/r:System.IO.Compression.dll"
    "/r:System.IO.Compression.FileSystem.dll"
    $source
  )
  & $csc @cscArgs

  if ($LASTEXITCODE -ne 0) { throw "csc завершился с кодом $LASTEXITCODE" }
  Write-Host "✓ собран: $out ($((Get-Item $out).Length) байт)"

  if ($Test) {
    $target = Join-Path $work "install-test"
    & $out --dir $target --force | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "установщик вернул код $LASTEXITCODE" }
    if (-not (Test-Path (Join-Path $target "anti-neuroslop\SKILL.md"))) { throw "установщик не создал SKILL.md" }
    if (-not (Test-Path (Join-Path $target "anti-neuroslop\references\katalog.md"))) { throw "установщик не распаковал references" }
    & $out --dir $target --uninstall | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "удаление вернуло код $LASTEXITCODE" }
    if (Test-Path (Join-Path $target "anti-neuroslop")) { throw "удаление не сработало" }
    Write-Host "✓ самопроверка установщика пройдена"
  }
}
finally {
  if (-not $KeepTemp) { Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue }
}
