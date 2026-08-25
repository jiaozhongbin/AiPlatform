---
name: roblox-studio-draft
description: "Write Studio drafts only. Never commit or publish. Load in the roblox-mvp-builder session."
---

# roblox-studio-draft

只写 Studio 草稿。不提交。不发布。不要删除已有实例或素材。

## Rules

- Exact replace against the current Studio text (including any existing draft). Do not overwrite a whole file when a precise edit will do.
- If local docs and Studio drift, Studio text (including draft) is the edit anchor.
- Do not Agent-commit or publish. The operator submits.
- End every run with a 变更表: added / modified instances and scripts, lobby and game instance listed separately when both exist.
