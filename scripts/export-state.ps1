<#
.SYNOPSIS
    打包 QQ 机器人的「状态」（配置 / 数据库 / 记忆 / 插件 / SnowLuma 配置），供跨机迁移。

.DESCRIPTION
    这些内容刻意不纳入 git（二进制 / 含密钥 / 每次都在变），迁移时用这个包拷一次即可。

    生成：<仓库>\_transfer\qqbot-state-<yyyyMMdd-HHmmss>.zip
    内含：
        astrbot-data\     配置、数据库、好感度、记忆、插件、知识库、T2I 模板
        snowluma-config\  OneBot 连接配置、WebUI 设置
        snowluma-data\    QQ 消息缓存（可用 -SkipSnowlumaData 去掉）

    数据库用 SQLite 在线备份接口复制，服务在跑也能拿到一致快照；
    但**仍然建议先 stop-all.bat**，因为配置和插件文件可能正被改写。

.PARAMETER SkipSnowlumaData
    不打包 snowluma\data（QQ 消息缓存，约 5 MB，丢了不影响机器人工作）。
#>
[CmdletBinding()]
param([switch]$SkipSnowlumaData)

$ErrorActionPreference = 'Stop'

$ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$DATA = Join-Path $ROOT 'astrbot\data'
$SNOW = Join-Path $ROOT 'snowluma'
$OUT = Join-Path $ROOT '_transfer'
$PY = Join-Path $ROOT 'runtime\python\cpython-3.12.15-windows-x86_64-none\python.exe'
$BACKUP = Join-Path $ROOT 'scripts\sqlite_backup.py'

if (-not (Test-Path $DATA)) { throw "找不到 $DATA" }
if (-not (Test-Path $PY)) { throw "找不到打包用的 python：$PY" }

if (Get-Process astrbot -ErrorAction SilentlyContinue) {
    Write-Host '注意：AstrBot 正在运行。数据库会走在线备份，但配置/插件可能正被改写。' -ForegroundColor Yellow
    Write-Host '      建议先 stop-all.bat 再打包。' -ForegroundColor Yellow
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$stage = Join-Path $env:TEMP "qqbot-state-$stamp"
New-Item -ItemType Directory -Force -Path $stage | Out-Null
$zip = Join-Path $OUT "qqbot-state-$stamp.zip"
New-Item -ItemType Directory -Force -Path $OUT | Out-Null

function Copy-Tree {
    param([string]$Source, [string]$Destination, [string[]]$ExcludeTop = @())

    if (-not (Test-Path $Source)) { return }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null

    Get-ChildItem $Source -Force | Where-Object { $_.Name -notin $ExcludeTop } | ForEach-Object {
        $target = Join-Path $Destination $_.Name

        if ($_.PSIsContainer) {
            Copy-Tree -Source $_.FullName -Destination $target
            return
        }
        if ($_.Name -match '\.db-(wal|shm)$') { return }

        if ($_.Extension -eq '.db') {
            & $PY $BACKUP $_.FullName $target
            if ($LASTEXITCODE -ne 0) { throw "数据库备份失败：$($_.FullName)" }
        } else {
            Copy-Item $_.FullName $target -Force
        }
    }
}

Write-Host '收集 AstrBot 数据 ...' -ForegroundColor DarkGray
Copy-Tree -Source $DATA -Destination (Join-Path $stage 'astrbot-data') `
    -ExcludeTop @('temp', 'logs', 'attachments', 'webchat', 'plugins.json')

Write-Host '收集 SnowLuma 配置 ...' -ForegroundColor DarkGray
Copy-Tree -Source (Join-Path $SNOW 'config') -Destination (Join-Path $stage 'snowluma-config')

if (-not $SkipSnowlumaData) {
    Write-Host '收集 SnowLuma 数据 ...' -ForegroundColor DarkGray
    Copy-Tree -Source (Join-Path $SNOW 'data') -Destination (Join-Path $stage 'snowluma-data')
}

$manifest = Join-Path $stage 'MANIFEST.txt'
@(
    "生成时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "来源机器: $env:COMPUTERNAME",
    "来源路径: $ROOT",
    '',
    '顶层内容:'
) + (Get-ChildItem $stage -Force | Select-Object -ExpandProperty Name) |
    Set-Content $manifest -Encoding UTF8

Write-Host '压缩 ...' -ForegroundColor DarkGray
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip -CompressionLevel Optimal
Remove-Item $stage -Recurse -Force

$sizeMB = [math]::Round((Get-Item $zip).Length / 1MB, 2)
Write-Host "`n完成: $zip  ($sizeMB MB)" -ForegroundColor Green
Write-Host '新机上解压后，把三个目录分别覆盖回对应位置。' -ForegroundColor DarkGray
