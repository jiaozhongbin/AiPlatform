# Roblox MVP

本地安装的 Kiro Crew 应用：在起始页选定项目文件夹，规划器写出玩法文档，确认后再由建造器通过 Studio MCP 搭一份可 Play 的草稿。

网关**不会**扫描仓库里的 `extras/`。只拉代码或只重启网关，侧边栏都不会出现这个应用。每台机器要自己安装并启用。清单里是 `defaultEnabled: false`。

源目录一律用仓库里的路径，不要用 `.worktrees\...`：

`D:\workspace\AiPlatform\extras\roblox-mvp`

下面命令默认在仓库根目录执行。本机 `kirocrew` 不在 PATH 时，改用：

```powershell
D:\workspace\AiPlatform\.venv\Scripts\kirocrew.exe
```

`npm run build` 会写出 `extras/roblox-mvp/ui/dist/index.mjs`。安装和更新都会把整个应用目录拷到 `~/.kiro/crew/apps/roblox-mvp/`，**没构建就更新会把已有起始页清掉**。不要提交 `ui/node_modules` 或 `ui/dist`。

## 新注册（这台机器第一次）

```powershell
cd D:\workspace\AiPlatform
git pull
cd extras\roblox-mvp\ui
npm install
npm run build
cd D:\workspace\AiPlatform
```

确认有 `extras\roblox-mvp\ui\dist\index.mjs` 后再装：

```powershell
kirocrew app install extras\roblox-mvp
```

若报 `already installed`，走「更新注册」，不要重复 install。

启用被第三方执行策略拦住时，先写入信任名单：

```powershell
kirocrew config set agent.apps_trusted '["roblox-mvp"]'
```

PowerShell 引号不对时用：

```powershell
kirocrew config set agent.apps_trusted "[`"roblox-mvp`"]"
```

然后启用：

```powershell
kirocrew app enable roblox-mvp
kirocrew app list
```

`roblox-mvp` 应为 `enabled`。再按下面「重启网关」启动或重启一次。

## 更新注册（已经装过、仓库有新提交）

不用再 `install` / `enable` / 写 `apps_trusted`。`kirocrew app install` 对已安装应用会失败。

```powershell
cd D:\workspace\AiPlatform
git pull
cd extras\roblox-mvp\ui
npm install
npm run build
cd D:\workspace\AiPlatform
```

只改了技能、后端或 agent JSON、没改 `ui/`，可以跳过 `npm`。只要这次会跑更新，起始页必须已经在源目录里（本次构建，或确认 `extras\roblox-mvp\ui\dist\index.mjs` 还在）。

把新文件拷进已安装副本。网关开着时，可用仪表盘：**Apps → Roblox MVP → 更新**。当初若是从 `.worktrees\...` 装的，更新源改成：

`D:\workspace\AiPlatform\extras\roblox-mvp`

没有仪表盘更新按钮时（CLI 没有 `kirocrew app update`）：

```powershell
cd D:\workspace\AiPlatform
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -c "from kiro_crew.apps.manager import update_app; r = update_app(r'D:\workspace\AiPlatform\extras\roblox-mvp', expected_name='roblox-mvp'); print(r.message or r.error)"
```

更新后按「重启网关」重启一次，让运行中的进程加载新拷贝。用仪表盘更新且当时已是 enabled，一般会自动重新注册；仍建议重启，避免吃到旧后端。

## 重启网关

| 步骤 | 做法 |
|------|------|
| 停 | `kirocrew stop`，或跑网关的窗口里 `Ctrl+C` |
| 起 | `kirocrew gateway` |
| 打开 | http://localhost:5476 |

本机上次使用的启动参数是 `kirocrew gateway --no-open`（不自动开浏览器）。不要连开两个网关抢同一端口。

停不掉而仪表盘仍能打开时：

```powershell
netstat -ano | findstr ":5476"
```

确认是 `kirocrew` / `python -m kiro_crew` 后再结束对应 PID。

## 验收

```powershell
kirocrew app info roblox-mvp
```

确认 `enabled`，`source` 指向 `D:\workspace\AiPlatform\extras\roblox-mvp`。浏览器打开 http://localhost:5476 ，侧边栏应有 **Roblox MVP**：选文件夹 → 开始。规划器写三个 md 可以马上验。

换电脑、换用户、或清过 `KIROCREW_HOME` / `~/.kiro/crew`，按「新注册」整套再来一遍。

## Studio MCP

建造器模板里的 `mcpServers.roblox-studio.command` 目前是占位启动命令（`npx -y roblox-studio-mcp`）。规划器模板没有 Studio MCP：`app.json` 也不再声明 `mcpServers`，避免启用时合并给规划器。

建造器要能写 Place，必须先改成部门真实的 Studio MCP 启动规格，并且在建造器 `tools` 白名单里显式加上 `@roblox-studio/<tool>` 名称。只改 `command`/`args` 不够：在补上这些工具名之前，建造器不能写 Studio。

使用建造器前，Roblox Studio 必须已打开并连上该 MCP。未打开 Studio 时不要指望写出草稿。

## 测试

在仓库根目录：

```bash
python -m pytest extras/roblox-mvp/tests -v --tb=short
```

Windows PowerShell：

```powershell
$env:PYTHONPATH = "src"
python -m pytest extras/roblox-mvp/tests -v --tb=short -n0
```
