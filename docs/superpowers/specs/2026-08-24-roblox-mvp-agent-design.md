# Roblox MVP Agent — Design

Department-local Kiro Crew app: a planner agent writes three reviewable
markdown files, a human confirms, a builder agent drafts a playable Roblox
place through the Studio MCP, and a human presses Play in Studio.

This is an agreed pre-implementation design. It is not a system spec. No
code in `src/kiro_crew/apps/builtins/` changes.

## Goal

A game-department operator can:

1. Open the app's start page, choose a folder, and start a planner chat.
2. Talk through one mechanic and one scene until three markdown files exist
   in that folder.
3. Explicitly confirm in chat.
4. Have a builder agent write Studio drafts that match those files.
5. Press Play in Studio themselves.

## Non-goals

- Shipping this app as a public builtin (`src/kiro_crew/apps/builtins/`).
- A spec-review workbench (side-by-side docs, phase machine, live preview).
- Lobby Place plus game-instance Place in one run.
- Dual-write to a git repo and Studio (Studio drafts only in v1).
- Auto-starting Play, screenshots, or feeding playtest results back.
- Calling an existing MVP generator. The builder writes the Place through
  Studio MCP.
- Changing the path mid-session. A new folder requires a new start-page run.

## Packaging

Installable local app. Source lives outside builtins, at `extras/roblox-mvp/`.
Internal registry distribution is out of scope for v1.

```
extras/roblox-mvp/
  app.json
  agents/roblox-mvp-spec.json
  agents/roblox-mvp-builder.json
  skills/roblox-mvp-docs/SKILL.md
  skills/roblox-studio-draft/SKILL.md
  skills/roblox-mvp-build/SKILL.md
  prompts/spec.md
  prompts/builder.md
  backend/          # pick-folder, path check, create planner session
  ui/               # start page only
```

Enable with `kirocrew app install extras/roblox-mvp` then
`kirocrew app enable roblox-mvp`. After enable, the two agents appear in
the agent roster and the start page appears in the sidebar.

`defaultEnabled` is false. `origin` is `local`, never `builtin`.

The start page lives in the app's own `ui/`, not `website/src/apps/`. Copy
is Chinese for the department. If the app is later promoted into the
dashboard tree, it must join the 12-locale catalog then; v1 does not.

## Start page

One route, no document preview.

Controls:

- **Choose folder** — opens a native directory dialog when the backend
  supports one.
- **Path field** — filled by the dialog; always editable. This is a
  first-class path, not a fallback hidden until failure.
- **Start** — disabled until the path is a usable absolute directory.

Start does four things, in order:

1. Backend validates the path (see Path rules).
2. Creates a chat slot with agent `roblox-mvp-spec`.
3. Sends a seed message that includes `PROJECT_DIR=<absolute path>` and
   the three required filenames.
4. Navigates to that slot.

The planner does not ask for a folder. A path spoken later in the chat is
ignored for writes; the seed `PROJECT_DIR` is the only location.

### Native dialog by host

The browser cannot return a real filesystem path. The app backend owns
`POST .../pick-folder`, off the event loop, one dialog at a time (409 if
already open).

| Host | Dialog | On failure |
|---|---|---|
| Windows | PowerShell `FolderBrowserDialog`, launched through `platform_compat.trusted_system_bin("powershell")` | Type the path |
| macOS | `osascript` choose-folder, same pattern as Design Tweak / Md Notebook | Type the path |
| Linux, unsupported, timeout, cancel | `501` / cancelled; UI keeps the field | Type the path |

Existing host pickers in this repo are macOS-only. Windows support is new
and stays inside this app. It is not a new gateway-wide API.

## Path rules

A usable `PROJECT_DIR` is all of:

- Absolute (Windows drive path or POSIX root).
- Existing directory (v1 does not create missing parents).
- Not a sensitive path (`security.py` / the same class of check
  Spec Builder uses for `working_dir`: `~/.ssh`, `~/.aws`, Kiro Crew
  keystone files under the data home, and the legacy `~/.kirocrew`
  deny list).

Reject with a machine-readable `code` and a short reason. Start stays
disabled / the request returns 4xx. The agent is never started on a
rejected path.

Writes go to the folder root, not a nested app-invented directory:

- `gameplay.md`
- `levels.md`
- `acceptance.md`

## Agents

Two agent templates, same split as PPTX Maker: the planner may spawn the
builder as a trusted subagent; the planner has no Studio tools.

### `roblox-mvp-spec` (planner)

- Tools: `read`, `write`, `glob`, `grep`, `use_subagent`.
- No `@roblox-studio/*` and no `mcpServers` entry for Studio.
- `toolsSettings.subagent.availableAgents` / `trustedAgents`:
  `["roblox-mvp-builder"]` only.
- Writes the three markdown files under `PROJECT_DIR`.
- Stops after writing and names the paths in chat.
- Calls `use_subagent` only after an explicit user confirmation
  (approval of the three files). Equivalent phrasing counts
  ("确认，开始搭", "looks good, build it"). Questions, edits, and
  "maybe later" do not.
- The spawn task includes the same `PROJECT_DIR` absolute path.

### `roblox-mvp-builder` (builder)

- Tools: `read`, `glob`, `grep`, plus an allowlist of Studio MCP tools
  that read the place and write drafts. No `use_subagent`.
- `mcpServers` includes the Studio server. The planner's template does
  not.
- Reads the three files first. If a file is missing or empty, stops and
  lists gaps. It does not invent requirements.
- Checks which Place the MCP is connected to before writing. If it
  cannot tell, stops.
- Writes drafts only. Does not commit, publish, or delete existing
  instances or assets.
- On Studio/MCP failure: stops, explains, does not edit the markdown.
- When Place and docs disagree: change the Place to match the confirmed
  docs. Do not edit the docs.
- Ends with a change table (added / modified instances and scripts).
  Does not claim Play passed.

`agent.model` is `"auto"` on both templates. No hardcoded model id.

## Documents

All three are complete, concrete, and free of placeholders.

**`gameplay.md`**

- One sentence: what the game is and what the player does.
- The single core mechanic.
- Inputs and win/lose conditions.
- One scene: objects and what each does.
- Explicit out-of-scope list.

**`levels.md`**

- Layout of that one scene (spawn, goal, obstacles).
- Numbers that matter (speed, health, score, time). Concrete values.
- If there is no economy, the file says so. No invented shop.

**`acceptance.md`**

- Checkboxes a human can verify in Studio Play.
- Examples: character spawns, player can reach the goal, failure
  restarts, no errors in the output.
- Last item is always: a human pressed Play in Studio. The agent does
  not mark the work complete.

Planner skill `roblox-mvp-docs` enforces: ask the few questions that
change the files; cut anything beyond one mechanic and one scene and say
what was cut.

## Skills

Registered on the app (`app.json` `skills[]`) so they install with it.
App Kit does not filter skills per agent. Role binding is the agent's
`prompt` plus `resources` (planner links only the docs skill; builder
links the two Studio skills). The planner can discover the builder
skills in the index; it still has no Studio tools.

| Skill | Agent | Content |
|---|---|---|
| `roblox-mvp-docs` | planner | Path is seed-only; interview questions; file shapes; scope cut |
| `roblox-studio-draft` | builder | Drafts only; no commit/publish; no delete of existing assets; exact replace against current Studio text; change table |
| `roblox-mvp-build` | builder | Map docs to instances/scripts; identify Place first; implement only what the docs state |

## Studio MCP

Declared on the app and on the builder template only. Registration uses
the App Kit `{app}:{server}` namespace so the server does not land in
`~/.kiro/settings/mcp.json`.

The launch spec (`command` / `args`, or `url`) is configuration in
`app.json` `mcpServers`, filled with the department's real Studio MCP
process before enable. There is no Cursor-IDE bridge and no hardcoded
plugin id.

If the launch spec is missing or the process fails: the builder session
starts, the first Studio call fails, the builder reports "Studio MCP
unavailable / Studio not running" and stops. Enable does not have to
preflight Studio (Studio is often closed when the app is enabled).

If the server exposes commit, publish, or delete-asset tools, they are
omitted from the builder `tools` list. Adding a tool to the server does
not grant it; the list is explicit.

Play stays a human action in Studio.

## Main flow

1. Operator opens **Roblox MVP**, chooses or types a folder, clicks Start.
2. Planner session opens with `PROJECT_DIR` in the seed.
3. Planner interviews, writes the three files, stops.
4. Operator edits files on disk or asks for revisions in chat. Planner
   updates the files. Still no Studio tools.
5. Operator confirms. Planner spawns `roblox-mvp-builder` with
   `PROJECT_DIR`.
6. Builder reads files, identifies Place, writes drafts, returns a
   change table.
7. Operator presses Play in Studio.

## Error handling

| Case | Behavior |
|---|---|
| Relative / missing / sensitive path | Start rejected; no slot |
| Native picker unsupported or cancelled | Field stays; operator types |
| Studio closed or MCP down | Builder stops; markdown unchanged |
| Docs incomplete | Builder stops with a gap list |
| Place identity unknown | Builder stops |
| User never confirms | Builder never starts |
| Scope larger than one mechanic / one scene | Planner cuts and states the cut |

## Tests (v1)

- Planner template `tools` contains no `@roblox-studio` entry and no
  Studio `mcpServers` key.
- Builder template `tools` contains no `use_subagent`.
- Builder `tools` is an explicit allowlist (no publish/commit names).
- Path check rejects relative, missing, and a sensitive home path; accepts
  an existing temp directory.
- `pick-folder` on a non-macOS/non-Windows host returns the unsupported
  code; Windows and macOS paths are unit-tested behind stubs, not a real
  dialog.
- Start-session seed includes `PROJECT_DIR` and the three filenames.
- Planner prompt/skill text forbids spawning before explicit confirmation.

No browser E2E in v1. No live Studio in CI.

## Later (not this design)

- Spec-review page (left docs, right chat, confirm button).
- Two Places (lobby and game instance) with two change tables.
- Local repo plus Studio dual-write.
- Genre templates (obby, tycoon, …) as extra skills.
- Internal registry distribution.
- Auto Play / screenshot loop, only if Studio MCP actually exposes it.
