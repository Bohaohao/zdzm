# 造梦终端 · 破妄法门

终端挂机 RPG。花果山篇，18 个阶段、6 个副本。

## 安装

**macOS / Linux**

```bash
curl -fsSL https://raw.githubusercontent.com/Bohaohao/zdzm/main/install.sh | bash
```

**Windows（PowerShell）**

```powershell
irm https://raw.githubusercontent.com/Bohaohao/zdzm/main/install.ps1 | iex
```

需要 Python 3.9+。安装时会自动装 pipx，不需要管理员权限。

**手动安装（三平台通用）**

```bash
pipx install git+https://github.com/Bohaohao/zdzm.git
```

## 使用

```bash
zdzm
```

存档在 `~/.zdzm/`，纯本地，不联网。

## 命令

```
status       角色面板
push         自动推图
farm 1-1     循环刷副本
enter        选副本进入
skills       技能加点（方向键）
loadout      技能装配
collect      收集进度
quit         存档退出
```
