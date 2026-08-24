# Roblox MVP

本地安装的 Kiro Crew 应用：在起始页选定项目文件夹，规划器写出玩法文档，确认后再由建造器通过 Studio MCP 搭一份可 Play 的草稿。

默认不启用（`defaultEnabled: false`）。安装前必须先构建 UI。

## 安装

在仓库根目录：

```bash
cd extras/roblox-mvp/ui
npm install
npm run build
cd ../../..
kirocrew app install extras/roblox-mvp
kirocrew app enable roblox-mvp
```

`npm run build` 会写出 `extras/roblox-mvp/ui/dist/index.mjs`。不要提交 `ui/node_modules` 或 `ui/dist`。

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
