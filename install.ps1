# 造梦终端 · Windows 绿色安装
# 用法：irm https://raw.githubusercontent.com/Bohaohao/zdzm/main/install.ps1 | iex
$ErrorActionPreference = "Stop"
$ZipUrl    = "https://github.com/Bohaohao/zdzm/archive/refs/heads/main.zip"
$InstallDir = Join-Path $env:LOCALAPPDATA "zdzm"
$BinDir     = Join-Path $env:USERPROFILE ".local\bin"

function Say($m) { Write-Host $m -ForegroundColor Cyan }
function Err($m) { Write-Host $m -ForegroundColor Red }

Say "==> 造梦终端"

# ---------- 1. 找一个真正能跑的 Python ----------
$py = $null
$pyLabel = $null
foreach ($c in @("py", "python3", "python")) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if (-not $cmd) { continue }
    try {
        $ver = (& $c -c "import sys;print('%d.%d'%sys.version_info[:2])" 2>$null | Out-String).Trim()
    } catch { $ver = "" }
    if ($ver -match '^\d+\.\d+$') {
        $major = [int]($ver.Split('.')[0])
        $minor = [int]($ver.Split('.')[1])
        if ($major -eq 3 -and $minor -ge 9) {
            $py = $c; $pyLabel = "Python $ver ($c)"; break
        }
    }
}
if (-not $py) {
    Err "未找到可用的 Python 3.9+"
    Err "下载：https://www.python.org/downloads/  （安装时勾选 Add python.exe to PATH）"
    Err "如果是从 Microsoft Store 装的占位符，请在「设置 > 应用 > 高级应用设置 > 应用执行别名」里关掉 python.exe"
    exit 1
}
Say "    $pyLabel"

# ---------- 1.5 强制清理旧版 ----------
# 不依赖 pipx 命令：直接删 venv 和 shim。
# Windows 上 .exe 优先于 .bat，pipx 的 zdzm.exe 会一直抢在绿色安装前面。
Say "==> 清理旧版"
$oldVenvs = @(
    (Join-Path $env:LOCALAPPDATA "pipx\pipx\venvs\zdzm"),
    (Join-Path $env:USERPROFILE ".local\pipx\venvs\zdzm")
)
foreach ($v in $oldVenvs) {
    if (Test-Path $v) {
        Remove-Item $v -Recurse -Force -ErrorAction SilentlyContinue
        Say "    已删除 $v"
    }
}
foreach ($ext in @("exe", "cmd", "bat")) {
    $f = Join-Path $BinDir "zdzm.$ext"
    if (Test-Path $f) {
        Remove-Item $f -Force -ErrorAction SilentlyContinue
        Say "    已删除 zdzm.$ext"
    }
}
# 若 pipx 还能用，顺手清掉它的记录，避免 list 里留残影
$pipxCmd = Get-Command pipx -ErrorAction SilentlyContinue
if ($pipxCmd) { & $pipxCmd.Source uninstall zdzm 2>$null | Out-Null }

# ---------- 2. 下载 zip ----------
Say "==> 下载源码"
$tmpZip = Join-Path $env:TEMP "zdzm-dl.zip"
$tmpDir = Join-Path $env:TEMP "zdzm-dl"
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $ZipUrl -OutFile $tmpZip -UseBasicParsing
} catch {
    Err "下载失败：$($_.Exception.Message)"
    Err "请检查网络能否访问 github.com"
    exit 1
}

# ---------- 3. 解压 ----------
Say "==> 解压到 $InstallDir"
if (Test-Path $tmpDir) { Remove-Item $tmpDir -Recurse -Force }
Expand-Archive -Path $tmpZip -DestinationPath $tmpDir -Force
if (Test-Path $InstallDir) { Remove-Item $InstallDir -Recurse -Force }
Move-Item (Join-Path $tmpDir "zdzm-main") $InstallDir
Remove-Item $tmpZip -Force -ErrorAction SilentlyContinue
Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue

# ---------- 4. 启动器 ----------
Say "==> 创建启动器"
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
$bat = @"
@echo off
set PYTHONPATH=$InstallDir
$py -m zdzm %*
"@
Set-Content -Path (Join-Path $BinDir "zdzm.bat") -Value $bat -Encoding ASCII

# ---------- 5. PATH ----------
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $userPath) { $userPath = "" }
if ($userPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", ($userPath.TrimEnd(';') + ";" + $BinDir), "User")
    Say "    已加入用户 PATH"
    $needRestart = $true
}

Say ""
Say "完成。"
if ($needRestart) {
    Say "请关掉这个窗口，重新打开终端，然后输入：zdzm"
} else {
    Say "重新打开终端后输入：zdzm"
}
Say "存档位置：$env:USERPROFILE\.zdzm\"
