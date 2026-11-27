# 造梦终端 · Windows 安装脚本
# 用法：irm https://raw.githubusercontent.com/Bohaohao/zdzm/main/install.ps1 | iex
$ErrorActionPreference = "Stop"
$Repo = "https://github.com/Bohaohao/zdzm.git"

function Say($m) { Write-Host $m -ForegroundColor Cyan }
function Err($m) { Write-Host $m -ForegroundColor Red }

Say "==> 造梦终端"

# 1. Python
$py = $null
foreach ($c in @("python", "py", "python3")) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd) { $py = $c; break }
}
if (-not $py) {
    Err "需要 Python 3.9+：https://www.python.org/downloads/"
    Err "安装时记得勾选 Add Python to PATH"
    exit 1
}
$ver = & $py -c "import sys;print('%d.%d'%sys.version_info[:2])"
Say "    Python $ver ($py)"

# 2. pipx
$hasPipx = $false
try { & $py -m pipx --version >$null 2>&1; $hasPipx = $true } catch { $hasPipx = $false }
if (-not $hasPipx) {
    Say "==> 安装 pipx"
    & $py -m pip install --user pipx
    if ($LASTEXITCODE -ne 0) {
        Err "pipx 安装失败，请手动执行：$py -m pip install --user pipx"
        exit 1
    }
}

# 3. 安装
Say "==> 拉取并安装"
& $py -m pipx install --force "git+$Repo"
if ($LASTEXITCODE -ne 0) {
    Err "安装失败。确认仓库可访问：$Repo"
    exit 1
}
& $py -m pipx ensurepath >$null 2>&1

Say ""
Say "完成。重开终端后输入：zdzm"
Say "如果提示找不到命令，关掉终端重开一次"
