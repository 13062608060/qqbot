<#
.SYNOPSIS
    离开一台机器之前跑这个：停服务 → 提交机器人数据 → 拉取 → 推送。

.DESCRIPTION
    QQ 机器人跟着你走，哪台开着哪台算数。所以「换机器」不是简单地 pull/push，
    而是一次交接：

        离开的那台：停服务   → 提交数据 → pull → push
        接手的那台：pull     → 起服务

    这个脚本负责前半段，handoff-in.ps1 负责后半段。

    为什么必须先停服务再提交：机器人运行时会持续改写好感度/记忆/插件 state，
    一边跑一边提交，推上去的可能是写了一半的状态。

.PARAMETER SkipStop
    不执行 stop-all.bat（等服务已经在别的终端停掉了再用）。

.PARAMETER Message
    自定义提交说明。默认自动带上时间和机器名。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\handoff-out.ps1
#>
[CmdletBinding()]
param(
    [switch]$SkipStop,
    [string]$Message
)

$ErrorActionPreference = 'Stop'
$ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

function Get-Git {
    $c = Get-Command git -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    $alt = Join-Path $env:USERPROFILE 'Tools\PortableGit\cmd\git.exe'
    if (Test-Path $alt) { return $alt }
    throw '找不到 git'
}

function Find-WorkspaceRepo {
    foreach ($p in @('E:\deepseek-work', 'J:\deepseek-work\workspace', 'C:\deepseek-work', 'D:\deepseek-work\workspace')) {
        if (Test-Path (Join-Path $p '.git')) {
            $remote = & $script:Git -C $p remote get-url origin 2>$null
            if ($remote -match 'dsh-workspace') { return $p }
        }
    }
    return $null
}

$Git = Get-Git
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm'

# ---------- 1. 停服务 ----------
Write-Host '[1/4] 停服务 ...' -ForegroundColor Cyan
if ($SkipStop) {
    Write-Host '      已指定 -SkipStop，跳过' -ForegroundColor DarkGray
} else {
    $stop = Join-Path $ROOT 'stop-all.bat'
    if (Test-Path $stop) { & $stop | Out-Null } else { Write-Host '      没找到 stop-all.bat' -ForegroundColor Yellow }

    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline) {
        $busy = Get-NetTCPConnection -LocalPort 6185, 6199, 5099 -State Listen -ErrorAction SilentlyContinue
        if (-not $busy) { break }
        Start-Sleep -Milliseconds 500
    }
    $still = Get-NetTCPConnection -LocalPort 6185, 6199, 5099 -State Listen -ErrorAction SilentlyContinue
    if ($still) {
        Write-Host "      端口仍被占用：$(($still.LocalPort | Sort-Object -Unique) -join ', ')" -ForegroundColor Yellow
        Write-Host '      建议手工确认后再继续，否则数据可能没落盘' -ForegroundColor Yellow
    } else {
        Write-Host '      已停止' -ForegroundColor DarkGray
    }
}

function Sync-Repo {
    param([string]$Path, [string]$Label)
    Write-Host "`n--- $Label ($Path)" -ForegroundColor Cyan
    Push-Location $Path
    try {
        $dirty = & $Git status --porcelain
        if ($dirty) {
            $msg = if ($Message) { $Message } else { "数据快照 $stamp @ $env:COMPUTERNAME" }
            & $Git add -A
            & $Git commit -q -m $msg
            Write-Host "      提交了 $(@($dirty).Count) 个改动：$msg" -ForegroundColor DarkGray
        } else {
            Write-Host '      没有改动' -ForegroundColor DarkGray
        }

        Write-Host '      拉取 ...' -ForegroundColor DarkGray
        & $Git pull --rebase --autostash
        if ($LASTEXITCODE -ne 0) {
            Write-Host '      拉取失败，可能有冲突 —— 先解决冲突再推' -ForegroundColor Red
            & $Git status --short | Select-Object -First 10
            return $false
        }

        Write-Host '      推送 ...' -ForegroundColor DarkGray
        & $Git push
        if ($LASTEXITCODE -ne 0) { Write-Host '      推送失败（网络或权限）' -ForegroundColor Red; return $false }

        $ahead = & $Git rev-list --count 'origin/main..HEAD'
        Write-Host "      完成，本地与远端一致（未推送 $ahead 条）" -ForegroundColor Green
        return $true
    } finally {
        Pop-Location
    }
}

# ---------- 2~4. 机器人仓库 + 工作区 ----------
$ok = Sync-Repo -Path $ROOT -Label 'QQ 机器人'

$ws = Find-WorkspaceRepo
if ($ws) {
    if (-not (Sync-Repo -Path $ws -Label '工作区')) { $ok = $false }
} else {
    Write-Host "`n--- 工作区：没找到（跳过）" -ForegroundColor Yellow
}

Write-Host "`n$(if ($ok) { '交接完成，可以在另一台机器上跑 handoff-in.ps1 了。' } else { '有步骤失败，先处理上面的错误。' })" `
    -ForegroundColor $(if ($ok) { 'Green' } else { 'Red' })

if ($ok) { exit 0 } else { exit 1 }
