#requires -Version 5.1
$script:ZombieTrayLanguageCodes = @('en', 'de', 'es', 'zh', 'ja', 'ru')
$script:ZombieTrayLanguageNames = [ordered]@{
    en = 'English'
    de = 'Deutsch'
    es = 'Español'
    zh = '中文'
    ja = '日本語'
    ru = 'Русский'
}
$script:ZombieTrayStrings = @{
    en = @{
        TooltipIdle = 'Zombie Killer: ready'
        TooltipAutoOn = 'Zombie Killer: on | interval {0} | age {1}'
        TooltipAutoOff = 'Zombie Killer: automatic off'
        MenuManual = 'Check and clean up stale MCPs'
        MenuAuto = 'Automatic'
        MenuInterval = 'Interval'
        MenuMinAge = 'Minimum process age'
        MenuLanguage = 'Language'
        MenuLog = 'Open log'
        MenuQuit = 'Quit tray'
    }
    de = @{
        TooltipIdle = 'Zombie-Killer: bereit'
        TooltipAutoOn = 'Zombie-Killer: an | Intervall {0} | Alter {1}'
        TooltipAutoOff = 'Zombie-Killer: Automatik aus'
        MenuManual = 'Jetzt prüfen und veraltete MCPs bereinigen'
        MenuAuto = 'Automatik'
        MenuInterval = 'Intervall'
        MenuMinAge = 'Mindestalter des Prozesses'
        MenuLanguage = 'Sprache'
        MenuLog = 'Log öffnen'
        MenuQuit = 'Tray beenden'
    }
    es = @{
        TooltipIdle = 'Zombie Killer: listo'
        TooltipAutoOn = 'Zombie Killer: activo | intervalo {0} | edad {1}'
        TooltipAutoOff = 'Zombie Killer: automático apagado'
        MenuManual = 'Comprobar y limpiar MCP obsoletos'
        MenuAuto = 'Automático'
        MenuInterval = 'Intervalo'
        MenuMinAge = 'Antigüedad mínima del proceso'
        MenuLanguage = 'Idioma'
        MenuLog = 'Abrir registro'
        MenuQuit = 'Salir de la bandeja'
    }
    zh = @{
        TooltipIdle = '僵尸清理：就绪'
        TooltipAutoOn = '僵尸清理：开启 | 间隔 {0} | 时长 {1}'
        TooltipAutoOff = '僵尸清理：自动关闭'
        MenuManual = '立即检查并清理过期 MCP'
        MenuAuto = '自动运行'
        MenuInterval = '间隔'
        MenuMinAge = '最短进程存续时间'
        MenuLanguage = '语言'
        MenuLog = '打开日志'
        MenuQuit = '退出托盘'
    }
    ja = @{
        TooltipIdle = 'ゾンビキラー：準備完了'
        TooltipAutoOn = 'ゾンビキラー：オン | 間隔 {0} | 経過 {1}'
        TooltipAutoOff = 'ゾンビキラー：自動オフ'
        MenuManual = '今すぐ確認して古い MCP を整理'
        MenuAuto = '自動実行'
        MenuInterval = '間隔'
        MenuMinAge = '最小プロセス存続時間'
        MenuLanguage = '言語'
        MenuLog = 'ログを開く'
        MenuQuit = 'トレイを終了'
    }
    ru = @{
        TooltipIdle = 'Zombie Killer: готов'
        TooltipAutoOn = 'Zombie Killer: вкл. | интервал {0} | возраст {1}'
        TooltipAutoOff = 'Zombie Killer: авто выкл.'
        MenuManual = 'Проверить и очистить старые MCP'
        MenuAuto = 'Автоматически'
        MenuInterval = 'Интервал'
        MenuMinAge = 'Минимальный возраст процесса'
        MenuLanguage = 'Язык'
        MenuLog = 'Открыть журнал'
        MenuQuit = 'Выйти из трея'
    }
}

function Get-ZombieTrayLanguageCodes {
    return $script:ZombieTrayLanguageCodes.Clone()
}

function Get-ZombieTrayDefaultLanguage {
    param([AllowNull()][string]$CultureName = '')
    if ([string]::IsNullOrWhiteSpace($CultureName)) {
        try {
            $CultureName = [System.Globalization.CultureInfo]::CurrentUICulture.Name
        } catch {
            return 'en'
        }
    }

    $code = ($CultureName.Trim() -split '[-_]')[0].ToLowerInvariant()
    if ($script:ZombieTrayLanguageCodes -contains $code) { return $code }
    return 'en'
}

function Resolve-ZombieTrayLanguage {
    param(
        [AllowNull()][object]$SavedLanguage,
        [AllowNull()][string]$CultureName = ''
    )
    if ($SavedLanguage -is [string]) {
        $candidate = $SavedLanguage.Trim().ToLowerInvariant()
        if ($script:ZombieTrayLanguageCodes -contains $candidate) { return $candidate }
    }
    return Get-ZombieTrayDefaultLanguage -CultureName $CultureName
}

function Get-ZombieTrayString {
    param([AllowNull()][string]$Language, [Parameter(Mandatory)][string]$Key)
    $code = Resolve-ZombieTrayLanguage -SavedLanguage $Language -CultureName 'en'
    $strings = $script:ZombieTrayStrings[$code]
    if (-not $strings.ContainsKey($Key)) {
        throw "Unknown tray string key: $Key"
    }
    return [string]$strings[$Key]
}

function Get-ZombieTrayTooltipText {
    param(
        [Parameter(Mandatory)][string]$Language,
        [Parameter(Mandatory)][bool]$Automatic,
        [string]$IntervalLabel = '',
        [string]$MinAgeLabel = '',
        [ValidateSet('auto', 'idle')][string]$Mode = 'auto'
    )
    if ($Mode -eq 'idle') {
        $text = Get-ZombieTrayString -Language $Language -Key 'TooltipIdle'
    } elseif ($Automatic) {
        $template = Get-ZombieTrayString -Language $Language -Key 'TooltipAutoOn'
        $text = $template -f $IntervalLabel, $MinAgeLabel
    } else {
        $text = Get-ZombieTrayString -Language $Language -Key 'TooltipAutoOff'
    }
    if ($text.Length -gt 63) {
        throw "Tray tooltip exceeds the 63-character Windows PowerShell compatibility limit: $($text.Length)"
    }
    return [string]$text
}

function Set-ZombieTrayTooltip {
    param(
        [Parameter(Mandatory)][object]$NotifyIcon,
        [Parameter(Mandatory)][string]$Language,
        [Parameter(Mandatory)][bool]$Automatic,
        [string]$IntervalLabel = '',
        [string]$MinAgeLabel = '',
        [ValidateSet('auto', 'idle')][string]$Mode = 'auto'
    )
    $text = Get-ZombieTrayTooltipText -Language $Language -Automatic $Automatic -IntervalLabel $IntervalLabel -MinAgeLabel $MinAgeLabel -Mode $Mode
    $NotifyIcon.Text = $text
    return $text
}

function New-ZombieTrayLanguageSelector {
    param([Parameter(Mandatory)][object]$Menu, [Parameter(Mandatory)][string]$CurrentLanguage)
    $selected = Resolve-ZombieTrayLanguage -SavedLanguage $CurrentLanguage -CultureName 'en'
    $items = @()
    foreach ($code in $script:ZombieTrayLanguageCodes) {
        $item = New-Object System.Windows.Forms.ToolStripMenuItem($script:ZombieTrayLanguageNames[$code])
        $item.Name = 'language-' + $code
        $item.Tag = $code
        $item.Checked = ($code -eq $selected)
        [void]$Menu.DropDownItems.Add($item)
        $items += $item
    }
    return ,$items
}

function Update-ZombieTrayMenuLanguage {
    param(
        [Parameter(Mandatory)][string]$Language,
        [Parameter(Mandatory)][System.Collections.IDictionary]$Controls,
        [Parameter(Mandatory)][object]$NotifyIcon,
        [Parameter(Mandatory)][bool]$Automatic,
        [Parameter(Mandatory)][int]$IntervalSeconds,
        [Parameter(Mandatory)][int]$MinAgeSeconds,
        [Parameter(Mandatory)][System.Collections.IDictionary]$IntervalLabelBySeconds,
        [Parameter(Mandatory)][System.Collections.IDictionary]$MinAgeLabelBySeconds
    )
    $code = Resolve-ZombieTrayLanguage -SavedLanguage $Language -CultureName 'en'
    $Controls['Manual'].Text = Get-ZombieTrayString -Language $code -Key 'MenuManual'
    $Controls['Auto'].Text = Get-ZombieTrayString -Language $code -Key 'MenuAuto'
    $Controls['Interval'].Text = Get-ZombieTrayString -Language $code -Key 'MenuInterval'
    $Controls['MinAge'].Text = Get-ZombieTrayString -Language $code -Key 'MenuMinAge'
    $Controls['Language'].Text = Get-ZombieTrayString -Language $code -Key 'MenuLanguage'
    $Controls['Log'].Text = Get-ZombieTrayString -Language $code -Key 'MenuLog'
    $Controls['Quit'].Text = Get-ZombieTrayString -Language $code -Key 'MenuQuit'

    foreach ($item in $Controls['LanguageItems']) {
        $item.Text = $script:ZombieTrayLanguageNames[[string]$item.Tag]
        $item.Checked = ([string]$item.Tag -eq $code)
    }

    $intervalLabel = [string]$IntervalLabelBySeconds[$IntervalSeconds]
    $minAgeLabel = [string]$MinAgeLabelBySeconds[$MinAgeSeconds]
    [void](Set-ZombieTrayTooltip -NotifyIcon $NotifyIcon -Language $code -Automatic $Automatic -IntervalLabel $intervalLabel -MinAgeLabel $minAgeLabel)
}

function Register-ZombieTrayLanguageSelection {
    param(
        [Parameter(Mandatory)][object[]]$Items,
        [Parameter(Mandatory)][object]$State,
        [Parameter(Mandatory)][System.Collections.IDictionary]$Controls,
        [Parameter(Mandatory)][object]$NotifyIcon,
        [Parameter(Mandatory)][System.Collections.IDictionary]$IntervalLabelBySeconds,
        [Parameter(Mandatory)][System.Collections.IDictionary]$MinAgeLabelBySeconds,
        [Parameter(Mandatory)][scriptblock]$SaveSettings,
        [scriptblock]$OnLanguageChanged
    )
    $languageCodes = $script:ZombieTrayLanguageCodes
    foreach ($item in $Items) {
        $handler = {
            $selected = ([string]$this.Tag).Trim().ToLowerInvariant()
            if ($languageCodes -notcontains $selected) { return }

            $State.Language = $selected
            foreach ($sibling in $Items) {
                $sibling.Checked = ([string]$sibling.Tag -eq $selected)
            }

            Update-ZombieTrayMenuLanguage -Language $selected -Controls $Controls -NotifyIcon $NotifyIcon -Automatic ([bool]$State.Automatic) -IntervalSeconds ([int]$State.IntervalSeconds) -MinAgeSeconds ([int]$State.MinAgeSeconds) -IntervalLabelBySeconds $IntervalLabelBySeconds -MinAgeLabelBySeconds $MinAgeLabelBySeconds
            & $SaveSettings ([bool]$State.Automatic) ([int]$State.IntervalSeconds) ([int]$State.MinAgeSeconds) $selected
            if ($OnLanguageChanged) { & $OnLanguageChanged $selected }
        }.GetNewClosure()
        $item.Add_Click($handler)
    }
}

function Save-AutomodeSettings {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][bool]$Automatic,
        [Parameter(Mandatory)][int]$IntervalSeconds,
        [Parameter(Mandatory)][int]$MinAgeSeconds,
        [Parameter(Mandatory)][string]$Language
    )
    $payload = [PSCustomObject]@{
        automatic = $Automatic
        interval_seconds = $IntervalSeconds
        min_age_seconds = $MinAgeSeconds
        language = $Language
    } | ConvertTo-Json -Compress
    Set-Content -LiteralPath $Path -Value $payload -Encoding UTF8
}

function Register-ZombieTraySettingSelection {
    param(
        [Parameter(Mandatory)][object]$AutoItem,
        [Parameter(Mandatory)][object[]]$IntervalItems,
        [Parameter(Mandatory)][object[]]$MinAgeItems,
        [Parameter(Mandatory)][object]$State,
        [Parameter(Mandatory)][scriptblock]$SaveSettings,
        [scriptblock]$OnAutomaticChanged,
        [scriptblock]$OnIntervalChanged,
        [scriptblock]$OnMinAgeChanged
    )

    $autoHandler = {
        $State.Automatic = -not [bool]$State.Automatic
        $this.Checked = [bool]$State.Automatic
        & $SaveSettings ([bool]$State.Automatic) ([int]$State.IntervalSeconds) ([int]$State.MinAgeSeconds) ([string]$State.Language)
        if ($OnAutomaticChanged) { & $OnAutomaticChanged ([bool]$State.Automatic) }
    }.GetNewClosure()
    $AutoItem.Add_Click($autoHandler)

    foreach ($item in $IntervalItems) {
        $intervalHandler = {
            $selected = [int]$this.Tag
            foreach ($sibling in $IntervalItems) { $sibling.Checked = ([int]$sibling.Tag -eq $selected) }
            $State.IntervalSeconds = $selected
            & $SaveSettings ([bool]$State.Automatic) $selected ([int]$State.MinAgeSeconds) ([string]$State.Language)
            if ($OnIntervalChanged) { & $OnIntervalChanged $selected }
        }.GetNewClosure()
        $item.Add_Click($intervalHandler)
    }

    foreach ($item in $MinAgeItems) {
        $minAgeHandler = {
            $selected = [int]$this.Tag
            foreach ($sibling in $MinAgeItems) { $sibling.Checked = ([int]$sibling.Tag -eq $selected) }
            $State.MinAgeSeconds = $selected
            & $SaveSettings ([bool]$State.Automatic) ([int]$State.IntervalSeconds) $selected ([string]$State.Language)
            if ($OnMinAgeChanged) { & $OnMinAgeChanged $selected }
        }.GetNewClosure()
        $item.Add_Click($minAgeHandler)
    }
}

Export-ModuleMember -Function Get-ZombieTrayLanguageCodes, Get-ZombieTrayDefaultLanguage, Resolve-ZombieTrayLanguage, Get-ZombieTrayString, Get-ZombieTrayTooltipText, Set-ZombieTrayTooltip, New-ZombieTrayLanguageSelector, Update-ZombieTrayMenuLanguage, Register-ZombieTrayLanguageSelection, Save-AutomodeSettings, Register-ZombieTraySettingSelection
