<#
.SYNOPSIS
    迁移后自检：确认 QQ 机器人目录在新机器上是完整可运行的。

.DESCRIPTION
    只做只读检查，不改任何东西。全绿再启动 start-all.bat。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\verify-env.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Continue'
$ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$EXPECTED = 'D:\deepseek-work\qqbot'
$fail = 0
$warn = 0

function Ok($m)   { Write-Host "  [OK]   $m" -ForegroundColor Green }
function Bad($m)  { Write-Host "  [FAIL] $m" -ForegroundColor Red;    $script:fail++ }
function Warn($m) { Write-Host "  [WARN] $m" -ForegroundColor Yellow; $script:warn++ }
function Head($m) { Write-Host "`n$m" -ForegroundColor Cyan }

Write-Host "QQ 机器人环境自检" -ForegroundColor White
Write-Host "目录: $ROOT"

Head "1. 路径"
if ($ROOT -ieq $EXPECTED) {
    Ok "路径与旧机一致"
} else {
    Bad "路径是 '$ROOT'，应为 '$EXPECTED'。venv 绑定绝对路径，换了路径 astrbot run 会失败。"
}

Head "2. Python 运行时"
$py = Join-Path $ROOT 'runtime\python\cpython-3.12.15-windows-x86_64-none\python.exe'
if (Test-Path $py) {
    $v = & $py -c "import sys;print(sys.version.split()[0])" 2>$null
    Ok "python $v"
} else {
    Bad "缺少 $py（runtime\ 没拷过来？）"
}
$launcher = Join-Path $ROOT 'runtime\bin\astrbot.exe'
if (Test-Path $launcher) { Ok 'AstrBot 启动器存在' } else { Bad '缺少 runtime\bin\astrbot.exe' }

Head "3. AstrBot"
$dist = Join-Path $ROOT 'runtime\tools\astrbot\Lib\site-packages'
if (Test-Path $dist) {
    $d = Get-ChildItem $dist -Directory -Filter 'astrbot-*.dist-info' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($d) { Ok "已安装 $($d.Name -replace '\.dist-info$','')" } else { Warn 'site-packages 里找不到 astrbot 的 dist-info' }
} else {
    Bad "缺少 $dist"
}

Head "4. SnowLuma"
$node = Join-Path $ROOT 'snowluma\node.exe'
$pkg  = Join-Path $ROOT 'snowluma\package.json'
if ((Test-Path $node) -and (Test-Path $pkg)) {
    $ver = (Get-Content $pkg -Raw -Encoding UTF8 | ConvertFrom-Json).version
    $nv  = & $node --version 2>$null
    Ok "snowluma $ver，自带 node $nv"
} else {
    Bad '缺少 snowluma\node.exe 或 package.json'
}

Head "5. 配置与密钥"
$cfg = Join-Path $ROOT 'astrbot\data\cmd_config.json'
$example = Join-Path $ROOT 'astrbot\data\cmd_config.example.json'
if (Test-Path $cfg) {
    $raw = Get-Content $cfg -Raw -Encoding UTF8
    if ($raw -match 'sk-[A-Za-z0-9]{20,}') { Ok 'cmd_config.json 存在，且含真实 API Key' }
    else { Warn 'cmd_config.json 存在，但没检测到真实 API Key（需跑 tools\apply_key_and_test.py）' }
} else {
    Bad '缺少 astrbot\data\cmd_config.json'
    if (Test-Path $example) {
        Write-Host "         可用模板重建： copy `"$example`" `"$cfg`"" -ForegroundColor DarkGray
    }
}

Head "6. 状态数据"
$db = Join-Path $ROOT 'astrbot\data\data_v4.db'
if (Test-Path $db) { Ok ("data_v4.db {0:N0} KB" -f ((Get-Item $db).Length/1KB)) } else { Warn '没有 data_v4.db（聊天记录为空）' }
foreach ($d in '大肥鱼好感度列表','大肥鱼记忆','plugins') {
    $p = Join-Path $ROOT "astrbot\data\$d"
    if (Test-Path $p) { Ok "$d 存在" } else { Warn "$d 不存在" }
}

Head "7. 端口"
$ports = @{ 6185 = 'AstrBot WebUI'; 6199 = 'OneBot 反向 WS'; 5099 = 'SnowLuma WebUI' }
foreach ($p in $ports.Keys | Sort-Object) {
    $inUse = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    if ($inUse) { Warn "$p ($($ports[$p])) 已被占用 —— 若服务已在跑则正常" }
    else        { Ok "$p ($($ports[$p])) 空闲" }
}

Head "8. 进程冲突"
$running = Get-Process astrbot,node -ErrorAction SilentlyContinue
if ($running) { Warn "已有 astrbot/node 在运行（可能旧机还在跑？同一 QQ 号会被互相踢下线）" } else { Ok '没有残留的 astrbot/node 进程' }

Head "9. Git"
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    # 本会话 PATH 可能还是旧的，回退到 PortableGit 常见安装位置
    $candidate = Join-Path $env:USERPROFILE 'Tools\PortableGit\cmd\git.exe'
    if (Test-Path $candidate) { $git = Get-Item $candidate }
}
if ($git) {
    $gitExe = if ($git -is [System.Management.Automation.CommandInfo]) { $git.Source } else { $git.FullName }
    Ok "$(& $gitExe --version) -> $gitExe"
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Warn '当前会话 PATH 里没有 git —— 新开一个终端即可（已写入用户 PATH）'
    }
    Push-Location $ROOT
    $branch = & $gitExe rev-parse --abbrev-ref HEAD 2>$null
    if ($LASTEXITCODE -eq 0) {
        Ok "当前分支 $branch"
        $dirty = & $gitExe status --porcelain 2>$null
        if ($dirty) { Warn "$(@($dirty).Count) 个文件未提交" } else { Ok '工作区干净' }
        $remote = & $gitExe remote -v 2>$null
        if ($remote) { Ok "已配置远程：$(@($remote)[0])" } else { Warn '未配置远程仓库（无法 push/pull）' }
    } else {
        Warn '这个目录还不是 git 仓库'
    }
    Pop-Location
} else {
    Warn 'git 未安装 —— 源码同步会不可用（不影响机器人本身运行）'
}

Write-Host "`n" -NoNewline
if ($fail -eq 0) {
    Write-Host "全部通过，可以启动： .\start-all.bat" -ForegroundColor Green
} else {
    Write-Host "$fail 项失败，$warn 项警告 —— 先按上面提示修" -ForegroundColor Red
}
Write-Host ("可用空间 D: {0:N1} GB" -f ((Get-PSDrive D).Free/1GB)) -ForegroundColor DarkGray

exit $fail
