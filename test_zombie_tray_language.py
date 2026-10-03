"""Exercise the real tray menu module without starting its worker or tray app."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import zombie_settings

ROOT = Path(__file__).resolve().parent
POWERSHELL = shutil.which("powershell.exe")


@pytest.mark.skipif(os.name != "nt" or POWERSHELL is None, reason="requires Windows PowerShell 5.1")
def test_tray_language_switch_preserves_menu_actions_and_tooltip_limits(tmp_path: Path) -> None:
    choice_payload = {
        "interval": [choice._asdict() for choice in zombie_settings.INTERVAL_CHOICES],
        "min_age": [choice._asdict() for choice in zombie_settings.MIN_AGE_CHOICES],
    }
    choices_path = tmp_path / "choices.json"
    choices_path.write_text(json.dumps(choice_payload, ensure_ascii=False), encoding="utf-8")

    script = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
Add-Type -AssemblyName System.Windows.Forms
Import-Module -Name $env:ZOMBIE_TRAY_UI_MODULE -Force
$choices = Get-Content -LiteralPath $env:ZOMBIE_TRAY_CHOICES -Raw -Encoding UTF8 | ConvertFrom-Json
$intervalLabels = @{}
foreach ($choice in $choices.interval) { $intervalLabels[[int]$choice.seconds] = [string]$choice.label }
$minAgeLabels = @{}
foreach ($choice in $choices.min_age) { $minAgeLabels[[int]$choice.seconds] = [string]$choice.label }
$script:stateFile = $env:ZOMBIE_TRAY_STATE
$script:currentAutomatic = $false
$script:currentInterval = 86400
$script:currentMinAge = 86400
$script:currentLanguage = 'en'
$script:intervalLabelBySeconds = $intervalLabels
$script:minAgeLabelBySeconds = $minAgeLabels
$script:workerEvents = New-Object 'System.Collections.Generic.List[string]'
$script:logMessages = New-Object 'System.Collections.Generic.List[string]'
function Get-DefaultLanguage { return Get-ZombieTrayDefaultLanguage }
function Write-TrayLog([string]$message) { $script:logMessages.Add($message) }
function Start-Worker([int]$intervalSeconds, [int]$minAgeSeconds) { $script:workerEvents.Add(('start:{0}:{1}' -f $intervalSeconds, $minAgeSeconds)) }
function Stop-Worker { $script:workerEvents.Add('stop') }
$sourceTokens = $null
$sourceErrors = $null
$trayAst = [System.Management.Automation.Language.Parser]::ParseFile($env:ZOMBIE_TRAY_SCRIPT, [ref]$sourceTokens, [ref]$sourceErrors)
if ($sourceErrors.Count) { throw 'tray source did not parse' }
$readerFunction = $trayAst.FindAll({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Get-AutomodeSettings' }, $true) | Select-Object -First 1
$tooltipFunction = $trayAst.FindAll({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Update-Tooltip' }, $true) | Select-Object -First 1
if (-not $readerFunction -or -not $tooltipFunction) { throw 'expected tray functions were not found' }
Invoke-Expression $readerFunction.Extent.Text
Invoke-Expression $tooltipFunction.Extent.Text
function Get-TrayAssignmentBlock([string]$Name) {
    $matches = $trayAst.FindAll({
        param($node)
        $node -is [System.Management.Automation.Language.AssignmentStatementAst] -and
        $node.Left -is [System.Management.Automation.Language.VariableExpressionAst] -and
        $node.Left.VariablePath.UserPath -eq $Name
    }, $true)
    if ($matches.Count -ne 1) { throw "expected one tray callback assignment for $Name, got $($matches.Count)" }
    return (Invoke-Expression $matches[0].Right.Extent.Text)
}

$currentUiCulture = [System.Globalization.CultureInfo]::CurrentUICulture
[System.Globalization.CultureInfo]::CurrentUICulture = [System.Globalization.CultureInfo]::GetCultureInfo('ja-JP')
$systemDefault = Get-ZombieTrayDefaultLanguage
[System.Globalization.CultureInfo]::CurrentUICulture = $currentUiCulture
if ($systemDefault -ne 'ja') { throw "culture default failed: $systemDefault" }
if ((Get-ZombieTrayDefaultLanguage -CultureName 'de-DE') -ne 'de') { throw 'German culture mapping failed' }
if ((Get-ZombieTrayDefaultLanguage -CultureName 'es_MX') -ne 'es') { throw 'underscore culture mapping failed' }
if ((Get-ZombieTrayDefaultLanguage -CultureName 'fr-FR') -ne 'en') { throw 'unknown culture must fall back to English' }
if ((Resolve-ZombieTrayLanguage -SavedLanguage 'ES' -CultureName 'de-DE') -ne 'es') { throw 'valid saved language must win' }
if ((Resolve-ZombieTrayLanguage -SavedLanguage 'bad' -CultureName 'de-DE') -ne 'de') { throw 'invalid saved language must use culture default' }
if ((Resolve-ZombieTrayLanguage -SavedLanguage $null -CultureName 'fr-FR') -ne 'en') { throw 'invalid culture must fall back to English' }

$rootMenu = New-Object System.Windows.Forms.ContextMenuStrip
$manual = New-Object System.Windows.Forms.ToolStripMenuItem
$auto = New-Object System.Windows.Forms.ToolStripMenuItem
$interval = New-Object System.Windows.Forms.ToolStripMenuItem
$minAge = New-Object System.Windows.Forms.ToolStripMenuItem
$language = New-Object System.Windows.Forms.ToolStripMenuItem
$log = New-Object System.Windows.Forms.ToolStripMenuItem
$quit = New-Object System.Windows.Forms.ToolStripMenuItem
foreach ($entry in @($manual, $auto, $interval, $minAge, $language, $log, $quit)) { [void]$rootMenu.Items.Add($entry) }
$notify = New-Object System.Windows.Forms.NotifyIcon
$script:notify = $notify
$state = [PSCustomObject]@{ Automatic = $false; IntervalSeconds = 86400; MinAgeSeconds = 86400; Language = 'en' }
$controls = @{ Manual = $manual; Auto = $auto; Interval = $interval; MinAge = $minAge; Language = $language; Log = $log; Quit = $quit }
$languageItems = New-ZombieTrayLanguageSelector -Menu $language -CurrentLanguage $state.Language
$controls.LanguageItems = $languageItems
$intervalItems = @()
foreach ($choice in $choices.interval) {
    $entry = New-Object System.Windows.Forms.ToolStripMenuItem([string]$choice.label)
    $entry.Tag = [int]$choice.seconds
    $entry.Checked = ([int]$choice.seconds -eq $state.IntervalSeconds)
    [void]$interval.DropDownItems.Add($entry)
    $intervalItems += $entry
}
$minAgeItems = @()
foreach ($choice in $choices.min_age) {
    $entry = New-Object System.Windows.Forms.ToolStripMenuItem([string]$choice.label)
    $entry.Tag = [int]$choice.seconds
    $entry.Checked = ([int]$choice.seconds -eq $state.MinAgeSeconds)
    [void]$minAge.DropDownItems.Add($entry)
    $minAgeItems += $entry
}
$clicks = New-Object 'System.Collections.Generic.List[string]'
$manual.Add_Click({ $clicks.Add('manual') })
$saveSettings = Get-TrayAssignmentBlock 'saveLanguageSettings'
$onLanguageChanged = Get-TrayAssignmentBlock 'onLanguageChanged'
$onAutomaticChanged = Get-TrayAssignmentBlock 'onAutomaticChanged'
$onIntervalChanged = Get-TrayAssignmentBlock 'onIntervalChanged'
$onMinAgeChanged = Get-TrayAssignmentBlock 'onMinAgeChanged'
Register-ZombieTrayLanguageSelection -Items $languageItems -State $state -Controls $controls -NotifyIcon $notify -IntervalLabelBySeconds $intervalLabels -MinAgeLabelBySeconds $minAgeLabels -SaveSettings $saveSettings -OnLanguageChanged $onLanguageChanged
Register-ZombieTraySettingSelection -AutoItem $auto -IntervalItems $intervalItems -MinAgeItems $minAgeItems -State $state -SaveSettings $saveSettings -OnAutomaticChanged $onAutomaticChanged -OnIntervalChanged $onIntervalChanged -OnMinAgeChanged $onMinAgeChanged

$codes = Get-ZombieTrayLanguageCodes
$expectedNames = @{ en = 'English'; de = 'Deutsch'; es = 'Español'; zh = '中文'; ja = '日本語'; ru = 'Русский' }
if (($codes -join ',') -ne 'en,de,es,zh,ja,ru') { throw "unexpected language codes: $($codes -join ',')" }
foreach ($item in $languageItems) {
    if ($item.Text -cne $expectedNames[[string]$item.Tag]) { throw "native language name mismatch for $($item.Tag)" }
}

Update-ZombieTrayMenuLanguage -Language 'en' -Controls $controls -NotifyIcon $notify -Automatic $state.Automatic -IntervalSeconds $state.IntervalSeconds -MinAgeSeconds $state.MinAgeSeconds -IntervalLabelBySeconds $intervalLabels -MinAgeLabelBySeconds $minAgeLabels
$renderedLengths = @{}
$maximumTooltipLength = 0
$switchCount = 0
foreach ($code in $codes) {
    $item = $languageItems | Where-Object { [string]$_.Tag -eq $code }
    $item.PerformClick()
    $switchCount += 1
    if ($state.Language -cne $code) { throw "selection did not update state for $code" }
    if ($switchCount -ne $renderedLengths.Count + 1) { throw "language callback count mismatch for $code" }
    $savedAfterLanguage = Get-Content -LiteralPath $env:ZOMBIE_TRAY_STATE -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($savedAfterLanguage.automatic -or $savedAfterLanguage.interval_seconds -ne 86400 -or $savedAfterLanguage.min_age_seconds -ne 86400 -or $savedAfterLanguage.language -cne $code) { throw "language save changed unrelated settings for $code" }
    if (($languageItems | Where-Object Checked).Count -ne 1 -or -not $item.Checked) { throw "language selection check state mismatch for $code" }
    foreach ($key in @('Manual', 'Auto', 'Interval', 'MinAge', 'Language', 'Log', 'Quit')) {
        if ([string]::IsNullOrWhiteSpace([string]$controls[$key].Text)) { throw "empty $key label in $code" }
    }
    if ($code -eq 'de' -and $controls.Manual.Text -notmatch 'prüfen') { throw 'German umlaut is missing from menu text' }

    foreach ($choice in $choices.interval) {
        foreach ($age in $choices.min_age) {
            $text = Set-ZombieTrayTooltip -NotifyIcon $notify -Language $code -Automatic $true -IntervalLabel ([string]$choice.label) -MinAgeLabel ([string]$age.label)
            if ($notify.Text -cne $text) { throw "NotifyIcon.Text did not preserve formatted tooltip for $code" }
            if ($notify.Text.Length -gt 63) { throw "tooltip exceeds WinPS5.1 limit for ${code}: $($notify.Text.Length)" }
            $maximumTooltipLength = [Math]::Max($maximumTooltipLength, $notify.Text.Length)
        }
    }
    foreach ($mode in @('idle', 'off')) {
        $text = Set-ZombieTrayTooltip -NotifyIcon $notify -Language $code -Automatic $false -Mode $(if ($mode -eq 'idle') { 'idle' } else { 'auto' })
        if ($notify.Text -cne $text -or $notify.Text.Length -gt 63) { throw "invalid $mode tooltip for $code" }
        $maximumTooltipLength = [Math]::Max($maximumTooltipLength, $notify.Text.Length)
    }
    $renderedLengths[$code] = $notify.Text.Length
}

# Updating labels must not replace the existing action delegates.
$manual.PerformClick()
$auto.PerformClick()
$intervalItems[0].PerformClick()
$minAgeItems[0].PerformClick()
$auto.PerformClick()
$languageItems[2].PerformClick()
if ($clicks.Count -ne 1 -or ($clicks -join ',') -ne 'manual') { throw 'manual menu action callback was lost during relabeling' }
if ($script:currentLanguage -cne 'es') { throw "outer script language state was not updated: $script:currentLanguage" }
$finalSettings = Get-Content -LiteralPath $env:ZOMBIE_TRAY_STATE -Raw -Encoding UTF8 | ConvertFrom-Json
if ($finalSettings.automatic -or $finalSettings.interval_seconds -ne [int]$intervalItems[0].Tag -or $finalSettings.min_age_seconds -ne [int]$minAgeItems[0].Tag -or $finalSettings.language -cne 'es') { throw 'follow-up settings callbacks did not retain selected language and chosen values' }
$expectedWorkerEvents = @('start:86400:86400', 'stop', ('start:{0}:86400' -f $intervalItems[0].Tag), 'stop', ('start:{0}:{1}' -f $intervalItems[0].Tag, $minAgeItems[0].Tag), 'stop')
if (($script:workerEvents -join ',') -cne ($expectedWorkerEvents -join ',')) { throw "unexpected worker callback sequence: $($script:workerEvents -join ',')" }

# Load the persisted settings through the real function body from zombie_tray.ps1.
$allowedInterval = @($choices.interval | ForEach-Object { [int]$_.seconds })
$allowedMinAge = @($choices.min_age | ForEach-Object { [int]$_.seconds })
$originalUiCulture = [System.Globalization.CultureInfo]::CurrentUICulture
try {
    [System.Globalization.CultureInfo]::CurrentUICulture = [System.Globalization.CultureInfo]::GetCultureInfo('de-DE')
    Save-AutomodeSettings -Path $script:stateFile -Automatic $true -IntervalSeconds 300 -MinAgeSeconds 600 -Language 'ru'
    $loaded = Get-AutomodeSettings -allowedInterval $allowedInterval -allowedMinAge $allowedMinAge
    if ($loaded.Language -cne 'ru') { throw 'saved language did not survive tray restart' }
    Save-AutomodeSettings -Path $script:stateFile -Automatic $true -IntervalSeconds 300 -MinAgeSeconds 600 -Language 'unsupported'
    $loaded = Get-AutomodeSettings -allowedInterval $allowedInterval -allowedMinAge $allowedMinAge
    if ($loaded.Language -cne 'de') { throw "unsupported saved language did not fall back to current culture: $($loaded.Language)" }
    [System.Globalization.CultureInfo]::CurrentUICulture = [System.Globalization.CultureInfo]::GetCultureInfo('fr-FR')
    $loaded = Get-AutomodeSettings -allowedInterval $allowedInterval -allowedMinAge $allowedMinAge
    if ($loaded.Language -cne 'en') { throw 'unsupported culture did not fall back to English' }
    [System.Globalization.CultureInfo]::CurrentUICulture = [System.Globalization.CultureInfo]::GetCultureInfo('es-ES')
    $script:stateFile = $env:ZOMBIE_TRAY_MISSING_STATE
    $loaded = Get-AutomodeSettings -allowedInterval $allowedInterval -allowedMinAge $allowedMinAge
    if ($loaded.Language -cne 'es' -or $loaded.Automatic -or $loaded.IntervalSeconds -ne 1800 -or $loaded.MinAgeSeconds -ne 1800) { throw 'missing settings did not use language/default values' }
} finally {
    [System.Globalization.CultureInfo]::CurrentUICulture = $originalUiCulture
    $script:stateFile = $env:ZOMBIE_TRAY_STATE
}
$result = [PSCustomObject]@{
    languages = @($codes)
    cultures = 'PASS'
    savedLanguageFallback = 'PASS'
    nativeNames = 'PASS'
    languageSwitches = $switchCount
    persistedSelections = 6 + 4
    callbacks = $clicks.Count
    tooltipCases = $codes.Count * $choices.interval.Count * $choices.min_age.Count
    settingCallbacks = 3
    outerLanguageState = $script:currentLanguage
    finalSettings = $finalSettings
    maximumLength = $maximumTooltipLength
    workerCallbacks = $script:workerEvents
    reloadCultureFallback = 'PASS'
}
$result | ConvertTo-Json -Compress
$notify.Dispose()
$rootMenu.Dispose()
"""
    script_path = tmp_path / "tray-language-check.ps1"
    script_path.write_bytes(b"\xef\xbb\xbf" + script.encode("utf-8"))

    env = os.environ.copy()
    env["ZOMBIE_TRAY_UI_MODULE"] = str(ROOT / "zombie_tray_ui.psm1")
    env["ZOMBIE_TRAY_CHOICES"] = str(choices_path)
    env["ZOMBIE_TRAY_STATE"] = str(tmp_path / "zombie_state.json")
    env["ZOMBIE_TRAY_MISSING_STATE"] = str(tmp_path / "missing-state.json")
    env["ZOMBIE_TRAY_SCRIPT"] = str(ROOT / "zombie_tray.ps1")
    completed = subprocess.run(
        [POWERSHELL, "-NoProfile", "-NonInteractive", "-Sta", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, f"PowerShell menu check failed: {completed.stdout}\n{completed.stderr}"
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    assert payload["languages"] == ["en", "de", "es", "zh", "ja", "ru"]
    assert payload["cultures"] == "PASS"
    assert payload["savedLanguageFallback"] == "PASS"
    assert payload["nativeNames"] == "PASS"
    assert payload["languageSwitches"] == 6
    assert payload["persistedSelections"] == 10
    assert payload["callbacks"] == 1
    assert payload["settingCallbacks"] == 3
    assert payload["outerLanguageState"] == "es"
    assert payload["finalSettings"] == {
        "automatic": False,
        "interval_seconds": zombie_settings.INTERVAL_CHOICES[0].seconds,
        "min_age_seconds": zombie_settings.MIN_AGE_CHOICES[0].seconds,
        "language": "es",
    }
    assert payload["workerCallbacks"] == [
        "start:86400:86400",
        "stop",
        "start:300:86400",
        "stop",
        "start:300:300",
        "stop",
    ]
    assert payload["reloadCultureFallback"] == "PASS"
    assert payload["tooltipCases"] == 6 * len(zombie_settings.INTERVAL_CHOICES) * len(zombie_settings.MIN_AGE_CHOICES)
    assert payload["maximumLength"] <= 63
