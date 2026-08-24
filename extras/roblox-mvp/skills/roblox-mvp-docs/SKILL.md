---
name: roblox-mvp-docs
description: "Write gameplay.md, levels.md, and acceptance.md for a one-mechanic Roblox MVP. Load in the roblox-mvp-spec planner session."
---

# roblox-mvp-docs

Load this skill in the planner session only. The seed `PROJECT_DIR` is the only write root. Ignore any later path spoken in chat.

## Interview

Ask the few questions that change the files. Keep the MVP to one mechanic and one scene. Cut anything larger and say what was cut.

## Files

Write these three files at the folder root, not in a nested directory:

- `gameplay.md` — what the game is, the single core mechanic, inputs and win/lose, the one scene, out-of-scope.
- `levels.md` — layout (spawn, goal, obstacles) and concrete numbers. If there is no economy, say so.
- `acceptance.md` — checkboxes a human can verify in Studio Play. Last item: a human pressed Play.

All three must be complete and free of placeholders. Stop after writing and name the paths.
