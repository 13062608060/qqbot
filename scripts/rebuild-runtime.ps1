<#
.SYNOPSIS
    在目标机器上从零重建 QQ 机器人的 Python 运行时（runtime\），不需要从源机拷贝那 1 GB。

.DESCRIPTION
    源机的 runtime\ 是 uv 建的环境：Python 3.12.15 + astrbot 4.29.1（154 个依赖包）。
    它绑死绝对路径，本来就不能整体复制。这个脚本用同样的配方重建：

        1. 取 uv（GitHub 官方发布，约 15 MB）
        2. uv 按原布局下载 Python 3.12.15 到 runtime\python\
        3. 在 runtime\tools\astrbot 建 venv，从阿里源装 astrbot==4.29.1
        4. 把 venv 里的 astrbot.exe 启动器复制到 runtime\bin\（原 start-astrbot.bat 可直接用）

    实测：154 个包，约 90 秒，版本与源机一致。

    ⚠️ 必须在 D:\deepseek-work\qqbot 下执行。venv 里写的是绝对路径，换目录必挂。

.PARAMETER Root
    仓库根目录，默认 D:\deepseek-work\qqbot

.PARAMETER AstrBotVersion
    默认 4.29.1（与源机一致）

.PARAMETER IndexUrl
    PyPI 镜像，默认阿里源

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\rebuild-runtime.ps1
#>
[CmdletBinding()]
param(
    [string]$Root = 'D:\deepseek-work\qqbot',
    [string]$AstrBotVersion = '4.29.1',
    [string]$IndexUrl = 'https://mirrors.aliyun.com/pypi/simple/'
)

$ErrorActionPreference = 'Stop'

$Expected = 'D:\deepseek-work\qqbot'
if ($Root -ne $Expected) {
    Write-Host "警告：Root 是 $Root，源机用的是 $Expected。路径不同会在以后换机时再踩一次坑。" -ForegroundColor Yellow
}
if (-not (Test-Path $Root)) { throw "找不到 $Root" }

$Runtime = Join-Path $Root 'runtime'
$Venv    = Join-Path $Runtime 'tools\astrbot'
$BinDir  = Join-Path $Runtime 'bin'
$UvExe   = Join-Path $BinDir 'uv.exe'
$PyDir   = Join-Path $Runtime 'python'

New-Item -ItemType Directory -Force -Path $Runtime, $BinDir | Out-Null

# ---------- 1. uv ----------
if (Test-Path $UvExe) {
    Write-Host "[1/5] uv 已存在：$(& $UvExe --version)" -ForegroundColor DarkGray
} else {
    Write-Host '[1/5] 下载 uv ...' -ForegroundColor Cyan
    $tmp = Join-Path $env:TEMP 'uv-download.zip'
    $url = 'https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip'
    Invoke-WebRequest $url -OutFile $tmp -UseBasicParsing -TimeoutSec 600
    $ext = Join-Path $env:TEMP 'uv-extract'
    if (Test-Path $ext) { Remove-Item $ext -Recurse -Force }
    Expand-Archive $tmp -DestinationPath $ext -Force
    Copy-Item (Join-Path $ext 'uv.exe') $UvExe -Force
    Copy-Item (Join-Path $ext 'uvx.exe') $BinDir -Force -ErrorAction SilentlyContinue
    Remove-Item $tmp, $ext -Recurse -Force
    Write-Host "      $(& $UvExe --version)" -ForegroundColor DarkGray
}

# ---------- 2. Python 3.12.15，装回 runtime\python\ ----------
# 关键：把 uv 的 Python 安装目录指回 runtime\python，
# 这样目录布局与源机完全一致（cpython-3.12.15-windows-x86_64-none\python.exe）。
$env:UV_PYTHON_INSTALL_DIR = $PyDir
Write-Host "[2/5] 准备 Python 3.12.15（安装到 $PyDir）..." -ForegroundColor Cyan
& $UvExe python install 3.12.15
if ($LASTEXITCODE -ne 0) {
    Write-Host '      3.12.15 不可用，退回最新的 3.12' -ForegroundColor Yellow
    & $UvExe python install 3.12
    if ($LASTEXITCODE -ne 0) { throw 'Python 下载失败，检查网络' }
}

# ---------- 3. venv ----------
Write-Host "[3/5] 在 $Venv 建 venv ..." -ForegroundColor Cyan
if (Test-Path $Venv) {
    Write-Host '      已存在，先删掉重建' -ForegroundColor DarkGray
    Remove-Item $Venv -Recurse -Force
}
& $UvExe venv --python 3.12.15 $Venv
if ($LASTEXITCODE -ne 0) { & $UvExe venv --python 3.12 $Venv }
if ($LASTEXITCODE -ne 0) { throw '创建 venv 失败' }

$VenvPy = Join-Path $Venv 'Scripts\python.exe'
if (-not (Test-Path $VenvPy)) { throw "没有生成 $VenvPy" }
Write-Host "      $(& $VenvPy -c 'import sys; print(sys.version.split()[0])')" -ForegroundColor DarkGray

# ---------- 4. 装 AstrBot ----------
Write-Host "[4/5] 安装 astrbot==$AstrBotVersion（$IndexUrl）..." -ForegroundColor Cyan
$sw = [Diagnostics.Stopwatch]::StartNew()
& $UvExe pip install --python $VenvPy --index-url $IndexUrl "astrbot==$AstrBotVersion"
if ($LASTEXITCODE -ne 0) { throw '安装 astrbot 失败' }
$sw.Stop()
Write-Host ("      耗时 {0:N0} 秒" -f $sw.Elapsed.TotalSeconds) -ForegroundColor DarkGray

# ---------- 5. 重建启动器 shim ----------
Write-Host '[5/5] 生成 runtime\bin\astrbot.exe ...' -ForegroundColor Cyan
$shimSrc = Join-Path $Venv 'Scripts\astrbot.exe'
if (-not (Test-Path $shimSrc)) { throw "venv 里没有 astrbot.exe：$shimSrc" }
Copy-Item $shimSrc (Join-Path $BinDir 'astrbot.exe') -Force
Write-Host "      $((Get-Item (Join-Path $BinDir 'astrbot.exe')).Length) 字节" -ForegroundColor DarkGray

# ---------- 校验 ----------
Write-Host "`n=== 校验 ===" -ForegroundColor Cyan
$dist = Get-ChildItem (Join-Path $Venv 'Lib\site-packages') -Directory -Filter 'astrbot-*.dist-info' -ErrorAction SilentlyContinue |
        Select-Object -First 1
if ($dist) { Write-Host "  astrbot: $($dist.Name -replace '\.dist-info$','')" -ForegroundColor Green }
else { throw 'site-packages 里找不到 astrbot 的 dist-info' }

$pkgCount = (& $UvExe pip list --python $VenvPy --format=freeze | Where-Object { $_ -match '==' }).Count
Write-Host "  依赖包: $pkgCount 个（源机基线 154）" -ForegroundColor Green

$ver = & (Join-Path $BinDir 'astrbot.exe') --version 2>&1 | Select-Object -First 1
Write-Host "  启动器: $ver" -ForegroundColor Green

if (Test-Path (Join-Path $Root 'astrbot\data\cmd_config.json')) {
    Write-Host "  配置:   存在" -ForegroundColor Green
} else {
    Write-Host "  配置:   缺失 —— 需要从状态包恢复" -ForegroundColor Yellow
}

Write-Host "`n运行时重建完成。下一步：" -ForegroundColor Green
Write-Host '  1. 恢复 SnowLuma：把 SnowLuma-v2.1.1-win-x64.zip 解压到 snowluma\' -ForegroundColor Gray
Write-Host '  2. 恢复状态：把 qqbot-state-*.zip 里的三个目录覆盖回原位' -ForegroundColor Gray
Write-Host '  3. 自检：  powershell -ExecutionPolicy Bypass -File scripts\verify-env.ps1' -ForegroundColor Gray
Write-Host '  4. 启动：  .\start-all.bat' -ForegroundColor Gray

exit 0
