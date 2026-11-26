<#
.SYNOPSIS
  MAN — My Anti-Neuroslop: установка скилла для Windows.

.EXAMPLE
  irm https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.ps1 | iex

.EXAMPLE
  .\install.ps1 -Target all -Force
#>
param(
  [ValidateSet("auto", "all", "claude", "opencode", "codex")]
  [string]$Target = "auto",
  [ValidateSet("user", "project")]
  [string]$Scope = "user",
  [string]$Dir,
  [string]$Version,
  [switch]$Force,
  [switch]$Uninstall,
  [switch]$DryRun,
  [switch]$Help
)

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$Repo = "crruton/MAN"
$Skill = "anti-neuroslop"
$HomeDir = $HOME

function Write-Say([string]$Text) { Write-Host $Text }
function Write-Ok([string]$Text) { Write-Host "✓ $Text" -ForegroundColor Green }
function Write-Warn2([string]$Text) { Write-Host "! $Text" -ForegroundColor Yellow }
function Fail([string]$Text) { Write-Host "× $Text" -ForegroundColor Red; exit 1 }

if ($Help) {
  @"
MAN — My Anti-Neuroslop

  install.ps1 [-Target auto|all|claude|opencode|codex] [-Scope user|project]
              [-Dir PATH] [-Version vX.Y.Z] [-Force] [-Uninstall] [-DryRun]

Примеры:
  irm https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.ps1 | iex
  .\install.ps1 -Target all
  .\install.ps1 -Uninstall
"@ | Write-Host
  exit 0
}

function Get-Dest([string]$Agent) {
  if ($Dir) { return $Dir }
  if ($Scope -eq "project") {
    switch ($Agent) {
      "claude" { return (Join-Path (Get-Location) ".claude\skills") }
      "opencode" { return (Join-Path (Get-Location) ".opencode\skills") }
      "codex" { return (Join-Path (Get-Location) ".codex\skills") }
    }
  }
  switch ($Agent) {
    "claude" { return (Join-Path $HomeDir ".claude\skills") }
    "opencode" { return (Join-Path $HomeDir ".config\opencode\skills") }
    "codex" { return (Join-Path $HomeDir ".codex\skills") }
  }
}

$agents = @()
if ($Dir) {
  $agents = @("custom")
}
elseif ($Target -eq "all") {
  $agents = @("claude", "opencode", "codex")
}
elseif ($Target -eq "auto") {
  if (Test-Path (Join-Path $HomeDir ".claude")) { $agents += "claude" }
  if (Test-Path (Join-Path $HomeDir ".config\opencode")) { $agents += "opencode" }
  if (Test-Path (Join-Path $HomeDir ".codex")) { $agents += "codex" }
  if ($agents.Count -eq 0) { $agents = @("claude") }
}
else {
  $agents = @($Target)
}

if ($Uninstall) {
  foreach ($agent in $agents) {
    $dest = Get-Dest $agent
    $skillDir = Join-Path $dest $Skill
    if (-not (Test-Path $skillDir)) {
      Write-Warn2 "не найдено: $skillDir"
      continue
    }
    if ((Test-Path (Join-Path $skillDir "SKILL.md")) -or $Force) {
      if ($DryRun) { Write-Ok "будет удалено: $skillDir" }
      else { Remove-Item -Recurse -Force $skillDir; Write-Ok "удалено: $skillDir" }
    }
    else {
      Fail "$skillDir не похож на скилл: нет SKILL.md"
    }
  }
  exit 0
}

$skillSrc = $null
if ($PSScriptRoot) { $skillSrc = Join-Path $PSScriptRoot "..\skills\$Skill" }
$tempDir = $null

if (-not $skillSrc -or -not (Test-Path (Join-Path $skillSrc "SKILL.md"))) {
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  $tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("man-" + [System.Guid]::NewGuid().ToString("N"))
  New-Item -ItemType Directory -Path $tempDir | Out-Null
  $archive = Join-Path $tempDir "skill.tar.gz"

  if ($Version) { $base = "https://github.com/$Repo/releases/download/$Version" }
  else { $base = "https://github.com/$Repo/releases/latest/download" }

  try {
    Invoke-WebRequest -UseBasicParsing -Uri "$base/man-skill.tar.gz" -OutFile $archive
    try {
      $sumsPath = Join-Path $tempDir "SHA256SUMS.txt"
      Invoke-WebRequest -UseBasicParsing -Uri "$base/SHA256SUMS.txt" -OutFile $sumsPath
      $line = Get-Content $sumsPath | Where-Object { $_ -match "\s\*?man-skill\.tar\.gz$" } | Select-Object -First 1
      if ($line) {
        $expected = ($line -split "\s+")[0].ToLower()
        $actual = (Get-FileHash -Algorithm SHA256 $archive).Hash.ToLower()
        if ($expected -ne $actual) { Fail "контрольная сумма не совпала" }
      }
    }
    catch { Write-Warn2 "не удалось проверить контрольную сумму" }
    Write-Say "→ Источник: релиз $(if ($Version) { $Version } else { 'latest' })"
  }
  catch {
    Write-Warn2 "релиз не найден, беру ветку main"
    Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/$Repo/tar.gz/refs/heads/main" -OutFile $archive
    Write-Say "→ Источник: ветка main"
  }

  $unpacked = Join-Path $tempDir "unpacked"
  New-Item -ItemType Directory -Path $unpacked | Out-Null
  tar -xzf $archive -C $unpacked
  $found = Get-ChildItem -Path $unpacked -Recurse -Filter "SKILL.md" |
    Where-Object { $_.Directory.Name -eq $Skill } | Select-Object -First 1
  if (-not $found) { Fail "в архиве не найден скилл $Skill" }
  $skillSrc = $found.Directory.FullName
}

$skillVersion = "unknown"
$skillMd = Join-Path $skillSrc "SKILL.md"
if (Test-Path $skillMd) {
  $m = Select-String -Path $skillMd -Pattern "^\s{2}version:\s*(\S+)" | Select-Object -First 1
  if ($m) { $skillVersion = $m.Matches[0].Groups[1].Value }
}

foreach ($agent in $agents) {
  $dest = Get-Dest $agent
  $skillDir = Join-Path $dest $Skill
  Write-Say "→ Цель: $skillDir"
  if (Test-Path $skillDir) {
    if (-not $Force) { Fail "скилл уже установлен в $skillDir. Обновите с -Force или удалите с -Uninstall" }
    if (-not (Test-Path (Join-Path $skillDir "SKILL.md"))) { Fail "$skillDir не похож на скилл: нет SKILL.md" }
    if (-not $DryRun) { Remove-Item -Recurse -Force $skillDir }
  }
  if ($DryRun) { Write-Ok "будет установлено: $skillDir"; continue }
  New-Item -ItemType Directory -Force -Path $dest | Out-Null
  Copy-Item -Recurse -Force $skillSrc $skillDir
  $installedAt = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
  $manifest = @"
{
  "skill": "$Skill",
  "version": "$skillVersion",
  "installed_at": "$installedAt",
  "source": "https://github.com/$Repo",
  "files": []
}
"@
  [System.IO.File]::WriteAllText((Join-Path $skillDir ".man.json"), $manifest, (New-Object System.Text.UTF8Encoding($false)))
  Write-Ok "установлено: $skillDir ($skillVersion)"
}

if ($tempDir -and (Test-Path $tempDir)) { Remove-Item -Recurse -Force $tempDir }

if (-not $DryRun) {
  Write-Say ""
  Write-Say "Что дальше:"
  Write-Say "  • Claude Code: /anti-neuroslop или «проверь текст на нейрослоп»"
  Write-Say "  • OpenCode, Codex: «перепиши, чтобы не пахло GPT»"
  Write-Say "  • Проверить установку: antislop doctor"
}
