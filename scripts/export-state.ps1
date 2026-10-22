<#
.SYNOPSIS
    把 AstrBot 的运行状态（配置、数据库、记忆、插件）打包成一个快照 zip，方便搬到另一台机器。

.DESCRIPTION
    这些内容刻意不纳入 git（二进制 / 含密钥），迁移时用这个脚本拷一次即可。

    生成： <仓库>\_transfer\qqbot-state-<yyyyMMdd-HHmmss>.zip
    内含： astrbot\data\ 下的配置、数据库、记忆、插件、知识库等
    排除： temp、logs、attachments、webchat、plugins.json

    新机用法：把 zip 解压后，把 astrbot\data 覆盖回仓库的 astrbot\data。

.PARAMETER Force
    即使检测到 AstrBot 正在运行也继续（不推荐：WAL 可能不完整）。
#>
[CmdletBinding()]
param([switch]$Force)

$ErrorActionPreference = 'Stop'
$ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$DATA = Join-Path $ROOT 'astrbot\data'
$OUT  = Join-Path $ROOT '_transfer'

if (-not (Test-Path $DATA)) { throw "找不到 $DATA" }

# AstrBot 在跑的时候直接拷 SQLite 有风险
$proc = Get-Process astrbot -ErrorAction SilentlyContinue
if ($proc -and -not $Force) {
    throw "AstrBot 正在运行（PID $($proc.Id)）。先执行 stop-all.bat，或加 -Force 强行打包。"
}

# 先把 WAL 合并回主库，避免快照丢最新消息
$db = Join-Path $DATA 'data_v4.db'
$py = Join-Path $ROOT 'runtime\python\cpython-3.12.15-windows-x86_64-none\python.exe'
if ((Test-Path $db) -and (Test-Path $py)) {
    Write-Host '合并 SQLite WAL ...' -ForegroundColor DarkGray
    & $py -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); print(c.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()); c.close()" $db
}

New-Item -ItemType Directory -Force -Path $OUT | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$zip = Join-Path $OUT "qqbot-state-$stamp.zip"
$stage = Join-Path $env:TEMP "qqbot-state-$stamp"
$stageData = Join-Path $stage 'astrbot-data'

Write-Host '收集文件 ...' -ForegroundColor DarkGray
New-Item -ItemType Directory -Force -Path $stageData | Out-Null
$exclude = @('temp', 'logs', 'attachments', 'webchat')

Get-ChildItem $DATA -Force | Where-Object {
    $_.Name -notin $exclude -and $_.Name -ne 'plugins.json'
} | ForEach-Object {
    Copy-Item $_.FullName -Destination $stageData -Recurse -Force
}

# 清单，方便核对
$manifest = Join-Path $stage 'MANIFEST.txt'
@(
    "生成时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "来源机器: $env:COMPUTERNAME",
    "来源路径: $ROOT",
    '',
    '顶层条目:'
) + (Get-ChildItem $stageData -Force | Select-Object -ExpandProperty Name) |
    Set-Content $manifest -Encoding UTF8

Write-Host '压缩 ...' -ForegroundColor DarkGray
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip -CompressionLevel Optimal
Remove-Item $stage -Recurse -Force

$sizeMB = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host "`n完成: $zip  ($sizeMB MB)" -ForegroundColor Green
Write-Host '新机上解压后，把 astrbot-data 里的内容覆盖回仓库的 astrbot\data 即可。' -ForegroundColor DarkGray
