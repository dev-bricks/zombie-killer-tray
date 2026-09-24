param([switch]$Preview)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$killer = Join-Path $root 'zombie_killer.py'
$log = Join-Path $root 'zombie_tray.log'
$stateFile = Join-Path $root 'zombie_state.json'
$python = (Get-Command python.exe -ErrorAction Stop).Source
$mutexName = 'Local\CodexZombieKillerTray-' + $env:USERNAME
$created = $false
$mutex = New-Object System.Threading.Mutex($true, $mutexName, [ref]$created)
if (-not $created) { $mutex.Dispose(); exit 0 }
$worker = $null
$notify = $null
$timer = $null
$menu = $null
$currentAutomatic = $false
$currentInterval = 1800
$currentMinAge = 1800
function Write-TrayLog([string]$message) {
    Add-Content -LiteralPath $log -Value ((Get-Date -Format o) + ' ' + $message) -Encoding UTF8
}
function Get-AutomodeChoices {
    # Single source of truth is zombie_settings.py's INTERVAL_CHOICES /
    # MIN_AGE_CHOICES -- read once at startup (one call, both lists)
    # instead of keeping a second, driftable copy of either table here.
    $pyCode = "import sys, json; sys.path.insert(0, r'$root'); import zombie_settings as s; " +
        "print(json.dumps({" +
        "'interval': [{'label': c.label, 'seconds': c.seconds} for c in s.INTERVAL_CHOICES], " +
        "'min_age': [{'label': c.label, 'seconds': c.seconds} for c in s.MIN_AGE_CHOICES]}))"
    $out = & $python -u -X utf8 -c $pyCode
    if ($LASTEXITCODE -ne 0) {
        throw "zombie_settings choice lists could not be read (exit $LASTEXITCODE)"
    }
    return ($out | ConvertFrom-Json)
}
function Get-AutomodeSettings([array]$allowedInterval, [array]$allowedMinAge) {
    # Fail-safe per field, mirroring zombie_settings.load_settings(): a
    # missing file, unreadable/corrupt JSON, or an out-of-range value
    # each fall back to the default for that ONE field, without discarding
    # an otherwise-valid other field. This is a convenience preference, not
    # a security gate -- the hard floor (min_age >= 30s, interval >= 3s)
    # lives in zombie_killer.py's own argument parser and is unchanged.
    $automatic = $false
    $intervalSeconds = 1800
    $minAgeSeconds = 1800
    if (Test-Path -LiteralPath $stateFile) {
        $data = $null
        try {
            $data = Get-Content -LiteralPath $stateFile -Raw -Encoding UTF8 | ConvertFrom-Json
        } catch {
            Write-TrayLog ('automode settings unreadable, using defaults: {0}' -f $_.Exception.Message)
        }
        if ($data) {
            if ($data.automatic -is [bool]) { $automatic = $data.automatic }
            if ($null -ne $data.interval_seconds -and ($allowedInterval -contains [int64]$data.interval_seconds)) {
                $intervalSeconds = [int]$data.interval_seconds
            }
            if ($null -ne $data.min_age_seconds -and ($allowedMinAge -contains [int64]$data.min_age_seconds)) {
                $minAgeSeconds = [int]$data.min_age_seconds
            }
        }
    }
    return [PSCustomObject]@{ Automatic = $automatic; IntervalSeconds = $intervalSeconds; MinAgeSeconds = $minAgeSeconds }
}
function Save-AutomodeSettings([bool]$automatic, [int]$intervalSeconds, [int]$minAgeSeconds) {
    $payload = [PSCustomObject]@{
        automatic = $automatic
        interval_seconds = $intervalSeconds
        min_age_seconds = $minAgeSeconds
    } | ConvertTo-Json -Compress
    Set-Content -LiteralPath $stateFile -Value $payload -Encoding UTF8
}
function Start-Worker([int]$intervalSeconds, [int]$minAgeSeconds) {
    # A single long-lived worker preserves observed parent identities. It uses Win32
    # directly and never launches taskkill/PowerShell descendants. No redirected pipes.
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $python
    $psi.Arguments = ('-u -X utf8 "{0}" watch --parent-pid {1} --interval {2} --min-age {3}' `
        -f $killer,$PID,$intervalSeconds,$minAgeSeconds)
    if (-not $Preview) { $psi.Arguments += ' --yes' }
    $psi.WorkingDirectory = $root
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.EnvironmentVariables['PYTHONIOENCODING'] = 'utf-8'
    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    [void]$proc.Start()
    $script:worker = $proc
    Write-TrayLog ('automode worker started worker_pid={0} interval={1}s min_age={2}s preview={3}' `
        -f $proc.Id,$intervalSeconds,$minAgeSeconds,$Preview)
}
function Stop-Worker {
    if ($script:worker) {
        if (-not $script:worker.HasExited) {
            $script:worker.Kill()
            [void]$script:worker.WaitForExit(5000)
        }
        Write-TrayLog ('automode worker stopped worker_pid={0}' -f $script:worker.Id)
        $script:worker.Dispose()
    }
    $script:worker = $null
}
function Invoke-ManualCleanup {
    if ($Preview) {
        $manualArguments = ('-u -X utf8 "{0}" scan' -f $killer)
    } else {
        $manualArguments = ('-u -X utf8 "{0}" reap --yes' -f $killer)
    }
    Write-TrayLog ('manual cleanup requested preview={0}' -f $Preview)
    $manualProcess = $null
    try {
        $manualInfo = New-Object System.Diagnostics.ProcessStartInfo
        $manualInfo.FileName = $python
        $manualInfo.Arguments = $manualArguments
        $manualInfo.WorkingDirectory = $root
        $manualInfo.UseShellExecute = $false
        $manualInfo.CreateNoWindow = $true
        $manualInfo.RedirectStandardOutput = $true
        $manualInfo.RedirectStandardError = $true
        $manualInfo.StandardOutputEncoding = [System.Text.Encoding]::UTF8
        $manualInfo.StandardErrorEncoding = [System.Text.Encoding]::UTF8
        $manualProcess = New-Object System.Diagnostics.Process
        $manualProcess.StartInfo = $manualInfo
        [void]$manualProcess.Start()
        $outTask = $manualProcess.StandardOutput.ReadToEndAsync()
        $errTask = $manualProcess.StandardError.ReadToEndAsync()
        if (-not $manualProcess.WaitForExit(15000)) {
            $manualProcess.Kill()
            [void]$manualProcess.WaitForExit(5000)
            Write-TrayLog 'manual cleanup timeout; helper stopped'
            return
        }
        $out = $outTask.Result.Trim() -replace '[\r\n]+',' '
        $err = $errTask.Result.Trim() -replace '[\r\n]+',' '
        Write-TrayLog ('manual cleanup rc={0} output={1} error={2}' -f $manualProcess.ExitCode,$out,$err)
    }
    catch {
        Write-TrayLog ('manual cleanup failed: {0}' -f $_.Exception.Message)
    }
    finally {
        if ($manualProcess) { $manualProcess.Dispose() }
    }
}
try {
    $choices = Get-AutomodeChoices
    $intervalChoices = $choices.interval
    $minAgeChoices = $choices.min_age
    $allowedInterval = @($intervalChoices | ForEach-Object { [int]$_.seconds })
    $allowedMinAge = @($minAgeChoices | ForEach-Object { [int]$_.seconds })
    $intervalLabelBySeconds = @{}
    foreach ($choice in $intervalChoices) { $intervalLabelBySeconds[[int]$choice.seconds] = $choice.label }
    $minAgeLabelBySeconds = @{}
    foreach ($choice in $minAgeChoices) { $minAgeLabelBySeconds[[int]$choice.seconds] = $choice.label }

    $settings = Get-AutomodeSettings -allowedInterval $allowedInterval -allowedMinAge $allowedMinAge
    $currentAutomatic = $settings.Automatic
    $currentInterval = $settings.IntervalSeconds
    $currentMinAge = $settings.MinAgeSeconds

    if ($currentAutomatic) { Start-Worker -intervalSeconds $currentInterval -minAgeSeconds $currentMinAge }
    Write-TrayLog ('started tray_pid={0} preview={1} automatic={2} interval={3}s min_age={4}s' `
        -f $PID,$Preview,$currentAutomatic,$currentInterval,$currentMinAge)

    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $notify = New-Object System.Windows.Forms.NotifyIcon
    $notify.Icon = [System.Drawing.SystemIcons]::Shield
    $notify.Visible = $true

    function Update-Tooltip {
        if ($script:currentAutomatic) {
            $script:notify.Text = ('Zombie-Killer: Auto an | Intervall {0} | Alter {1}' `
                -f $script:intervalLabelBySeconds[$script:currentInterval], $script:minAgeLabelBySeconds[$script:currentMinAge])
        } else {
            $script:notify.Text = 'Zombie-Killer: Automatik aus'
        }
    }
    Update-Tooltip

    $menu = New-Object System.Windows.Forms.ContextMenuStrip
    $manual = $menu.Items.Add('Jetzt pr' + [char]0x00FC + 'fen und veraltete MCPs bereinigen')

    $autoToggle = New-Object System.Windows.Forms.ToolStripMenuItem('Automatik')
    $autoToggle.Checked = $currentAutomatic
    [void]$menu.Items.Add($autoToggle)

    $intervalMenu = New-Object System.Windows.Forms.ToolStripMenuItem('Intervall')
    [void]$menu.Items.Add($intervalMenu)
    $allIntervalItems = @()
    foreach ($choice in $intervalChoices) {
        $item = New-Object System.Windows.Forms.ToolStripMenuItem([string]$choice.label)
        $item.Tag = [int]$choice.seconds
        $item.Checked = ([int]$choice.seconds -eq $currentInterval)
        [void]$intervalMenu.DropDownItems.Add($item)
        $allIntervalItems += $item
    }

    $minAgeMenu = New-Object System.Windows.Forms.ToolStripMenuItem('Mindestwartezeit')
    [void]$menu.Items.Add($minAgeMenu)
    $allMinAgeItems = @()
    foreach ($choice in $minAgeChoices) {
        $item = New-Object System.Windows.Forms.ToolStripMenuItem([string]$choice.label)
        $item.Tag = [int]$choice.seconds
        $item.Checked = ([int]$choice.seconds -eq $currentMinAge)
        [void]$minAgeMenu.DropDownItems.Add($item)
        $allMinAgeItems += $item
    }

    $open = $menu.Items.Add(('Log ' + [char]0x00F6 + 'ffnen'))
    $quit = $menu.Items.Add('Tray beenden')
    $notify.ContextMenuStrip = $menu

    $manual.Add_Click({
        $manual.Enabled = $false
        try { Invoke-ManualCleanup } finally { $manual.Enabled = $true }
    })
    $autoToggle.Add_Click({
        $script:currentAutomatic = -not $script:currentAutomatic
        $this.Checked = $script:currentAutomatic
        Save-AutomodeSettings $script:currentAutomatic $script:currentInterval $script:currentMinAge
        if ($script:currentAutomatic) {
            Start-Worker -intervalSeconds $script:currentInterval -minAgeSeconds $script:currentMinAge
        } else {
            Stop-Worker
        }
        Update-Tooltip
        Write-TrayLog ('automatic mode toggled to {0}' -f $script:currentAutomatic)
    })
    foreach ($item in $allIntervalItems) {
        $item.Add_Click({
            $selected = [int]$this.Tag
            foreach ($sibling in $allIntervalItems) { $sibling.Checked = ($sibling -eq $this) }
            $script:currentInterval = $selected
            Save-AutomodeSettings $script:currentAutomatic $script:currentInterval $script:currentMinAge
            Update-Tooltip
            Write-TrayLog ('automode interval set to {0}s' -f $selected)
            if ($script:currentAutomatic) {
                Stop-Worker
                Start-Worker -intervalSeconds $script:currentInterval -minAgeSeconds $script:currentMinAge
            }
        })
    }
    foreach ($item in $allMinAgeItems) {
        $item.Add_Click({
            $selected = [int]$this.Tag
            foreach ($sibling in $allMinAgeItems) { $sibling.Checked = ($sibling -eq $this) }
            $script:currentMinAge = $selected
            Save-AutomodeSettings $script:currentAutomatic $script:currentInterval $script:currentMinAge
            Update-Tooltip
            Write-TrayLog ('automode min-age set to {0}s' -f $selected)
            if ($script:currentAutomatic) {
                Stop-Worker
                Start-Worker -intervalSeconds $script:currentInterval -minAgeSeconds $script:currentMinAge
            }
        })
    }
    $open.Add_Click({ Start-Process notepad.exe -ArgumentList ('"{0}"' -f $log) })
    $quit.Add_Click({ [System.Windows.Forms.Application]::Exit() })
    $notify.Add_DoubleClick({ Invoke-ManualCleanup })

    $timer = New-Object System.Windows.Forms.Timer
    $timer.Interval = 10000
    $timer.Add_Tick({
        if ($script:worker -and $script:worker.HasExited) {
            Write-TrayLog ('worker exited rc={0}; no automatic restart' -f $script:worker.ExitCode)
            [System.Windows.Forms.Application]::Exit()
        }
    })
    $timer.Start()
    [System.Windows.Forms.Application]::Run()
}
finally {
    if ($timer) { $timer.Stop(); $timer.Dispose() }
    if ($notify) { $notify.Visible = $false; $notify.Dispose() }
    if ($menu) { $menu.Dispose() }
    Stop-Worker
    Write-TrayLog 'tray stopped'
    $mutex.ReleaseMutex()
    $mutex.Dispose()
}
