<#
.SYNOPSIS
    换到一台机器上开始工作前跑这个：拉取 → 起服务。

.DESCRIPTION
    和 handoff-out.ps1 配对使用。在离开那台机器上跑完 handoff-out 之后，
    到这台机器上跑这个，把最新的机器人数据拉下来再启动。

    启动前请确认：
      1. 另一台机器上的服务已经停了（这个脚本检测不到，靠你保证）
      2. 本机的 QQ 小号已经登录（SnowLuma 要挂在已登录的 QQ 进程上）

.PARAMETER SkipStart
    只拉取，不启动服务。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\handoff-in.ps1
#>
[CmdletBinding()]
param([switch]$SkipStart)

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

# ---------- 0. 安全检查 ----------
$running = Get-Process astrbot -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "注意：本机已有 AstrBot 在运行（PID $($running.Id)）。" -ForegroundColor Yellow
    Write-Host '      如果要重新拉数据，应先 stop-all.bat。' -ForegroundColor Yellow
}

# ---------- 1. 拉取 ----------
function Sync-Repo {
    param([string]$Path, [string]$Label)
    Write-Host "`n--- $Label ($Path)" -ForegroundColor Cyan
    Push-Location $Path
    try {
        $dirty = & $Git status --porcelain
        if ($dirty) {
            Write-Host "      本地有 $(@($dirty).Count) 个未提交改动，pull 时用 autostash 暂存" -ForegroundColor Yellow
        }
        & $Git pull --rebase --autostash
        if ($LASTEXITCODE -ne 0) {
            Write-Host '      拉取失败，可能有冲突' -ForegroundColor Red
            & $Git status --short | Select-Object -First 10
            return $false
        }
        $behind = & $Git rev-list --count 'HEAD..origin/main'
        $head = & $Git rev-parse --short HEAD
        Write-Host "      已同步到 $head（落后 $behind 条）" -ForegroundColor Green
        return $true
    } finally {
        Pop-Location
    }
}

$ok = Sync-Repo -Path $ROOT -Label 'QQ 机器人'
$ws = Find-WorkspaceRepo
if ($ws) { if (-not (Sync-Repo -Path $ws -Label '工作区')) { $ok = $false } }

if (-not $ok) {
    Write-Host "`n拉取有问题，先别启动服务。" -ForegroundColor Red
    exit 1
}

if ($SkipStart) {
    Write-Host "`n已跳过启动（-SkipStart）。" -ForegroundColor DarkGray
    exit 0
}

# ---------- 2. 起服务 ----------
Write-Host "`n[2/2] 启动服务 ..." -ForegroundColor Cyan
Write-Host '  提醒：本机 QQ 小号需要已登录，否则 SnowLuma 挂不上。' -ForegroundColor Yellow

$start = Join-Path $ROOT 'start-all.bat'
if (-not (Test-Path $start)) { throw "找不到 $start" }

# 不要写成 & $start | Out-Null：
# start-all.bat 里用 start 拉起两个子窗口，子进程会继承管道的 stdout 句柄，
# 管道迟迟不关闭，这里就会无限期挂住（表现为「卡住不动」）。
# 用 Start-Process 分离，调用方立刻拿到控制权。
Start-Process -FilePath $start -WindowStyle Minimized

$deadline = (Get-Date).AddSeconds(90)
while ((Get-Date) -lt $deadline) {
    $listen = Get-NetTCPConnection -LocalPort 6185 -State Listen -ErrorAction SilentlyContinue
    if ($listen) { break }
    Start-Sleep -Seconds 1
}

$ports = foreach ($p in 6185, 6199, 5099) {
    $up = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    "$p=$(if ($up) { 'up' } else { 'down' })"
}
Write-Host "`n端口：$($ports -join '  ')" -ForegroundColor Cyan
Write-Host 'AstrBot  http://127.0.0.1:6185' -ForegroundColor Gray
Write-Host 'SnowLuma http://127.0.0.1:5099' -ForegroundColor Gray

if ($ports -match 'down') {
    Write-Host "`n有端口没起来，看 astrbot\data\logs\ 最新日志。" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n交接完成。" -ForegroundColor Green
exit 0
