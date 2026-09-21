param([switch]$Preview)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$killer = Join-Path $root 'zombie_killer.py'
$log = Join-Path $root 'zombie_tray.log'
$python = (Get-Command python.exe -ErrorAction Stop).Source
$mutexName = 'Local\CodexZombieKillerTray-' + $env:USERNAME
$created = $false
$mutex = New-Object System.Threading.Mutex($true, $mutexName, [ref]$created)
if (-not $created) { $mutex.Dispose(); exit 0 }
$worker = $null
$notify = $null
$timer = $null
$menu = $null
function Write-TrayLog([string]$message) {
    Add-Content -LiteralPath $log -Value ((Get-Date -Format o) + ' ' + $message) -Encoding UTF8
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
    # A single long-lived worker preserves observed parent identities. It uses Win32
    # directly and never launches taskkill/PowerShell descendants. No redirected pipes.
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $python
    $psi.Arguments = ('-u -X utf8 "{0}" watch --parent-pid {1}' -f $killer,$PID)
    if (-not $Preview) { $psi.Arguments += ' --yes' }
    $psi.WorkingDirectory = $root
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.EnvironmentVariables['PYTHONIOENCODING'] = 'utf-8'
    $worker = New-Object System.Diagnostics.Process
    $worker.StartInfo = $psi
    [void]$worker.Start()
    Write-TrayLog ('started tray_pid={0} worker_pid={1} preview={2}' -f $PID,$worker.Id,$Preview)
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $notify = New-Object System.Windows.Forms.NotifyIcon
    $notify.Icon = [System.Drawing.SystemIcons]::Shield
    $notify.Text = 'Zombie-Killer: sichere Bereinigung'
    $notify.Visible = $true
    $menu = New-Object System.Windows.Forms.ContextMenuStrip
    $manual = $menu.Items.Add('Jetzt pr' + [char]0x00FC + 'fen und veraltete MCPs bereinigen')
    $open = $menu.Items.Add(('Log ' + [char]0x00F6 + 'ffnen'))
    $quit = $menu.Items.Add('Tray beenden')
    $notify.ContextMenuStrip = $menu
    $manual.Add_Click({
        $manual.Enabled = $false
        try { Invoke-ManualCleanup } finally { $manual.Enabled = $true }
    })
    $open.Add_Click({ Start-Process notepad.exe -ArgumentList ('"{0}"' -f $log) })
    $quit.Add_Click({ [System.Windows.Forms.Application]::Exit() })
    $notify.Add_DoubleClick({ Invoke-ManualCleanup })
    $timer = New-Object System.Windows.Forms.Timer
    $timer.Interval = 10000
    $timer.Add_Tick({
        if ($worker.HasExited) {
            Write-TrayLog ('worker exited rc={0}; no automatic restart' -f $worker.ExitCode)
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
    if ($worker) {
        if (-not $worker.HasExited) { $worker.Kill(); [void]$worker.WaitForExit(5000) }
        $worker.Dispose()
    }
    Write-TrayLog 'tray stopped'
    $mutex.ReleaseMutex()
    $mutex.Dispose()
}
