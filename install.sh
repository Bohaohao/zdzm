#!/usr/bin/env bash
set -e

REPO="${ZDZM_REPO:-https://github.com/Bohaohao/zdzm.git}"

say() { printf "\033[36m%s\033[0m\n" "$*"; }
err() { printf "\033[31m%s\033[0m\n" "$*" >&2; }

say "==> 造梦终端"

# 1. Python
if ! command -v python3 >/dev/null 2>&1; then
  err "需要 Python 3.9+：https://www.python.org/downloads/"
  exit 1
fi
PYV=$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')
say "    Python $PYV"

# 2. pipx（优先 brew，避免 externally-managed-environment）
if ! command -v pipx >/dev/null 2>&1; then
  say "==> 安装 pipx"
  if command -v brew >/dev/null 2>&1; then
    brew install pipx
  elif python3 -m pip install --user pipx >/dev/null 2>&1; then
    :
  elif python3 -m pip install --user --break-system-packages pipx >/dev/null 2>&1; then
    :
  else
    err "pipx 安装失败。手动执行：python3 -m pip install --user pipx"
    exit 1
  fi
  python3 -m pipx ensurepath >/dev/null 2>&1 || true
fi

# 3. 安装
say "==> 拉取并安装"
pipx install --force "git+${REPO}" || {
  err "安装失败。确认仓库可访问：${REPO}"
  exit 1
}

say ""
say "完成。新开终端后输入：zdzm"
say "找不到命令就执行 pipx ensurepath，然后重开终端"
