# Boyd Workstation — upgrade brainstorm
**Date:** 2026-09-21 ~03:03 EDT · **Author:** Vera · **Status:** brainstorm (no build yet)

## What it is today (v2)
Tabs: Chat · NPC · Code · Ops/MCP  
- Local Ollama `127.0.0.1:11434` (models ≤7b listed; default `qwen3:1.7b`)
- Ops: real Funnel MCP `tools/call` read-only allowlist + vault read + knowledge search
- Fixed: Gradio 6 multimodal `[{text,type}]` history unwrap
- Tailscale Serve → `:7860`
- NOT: tool-using chat agent, dual-VM swarm, OpenCode, Keep live feed, browser CDP, writes/gates

## North star (when Grok chat is dead)
Jason opens one URL and can: talk to local models, check fortress health, read vault/knowledge, get coding help, feel Keep NPCs — without cloud AI.

## Three approaches
**A — Solo Ops Console (recommended)**  
Deepen Ops + Chat-with-tools; skip Command Deck theater. Lowest fake, highest survival value.

**B — Ravenstack Command Deck**  
Swarm benchmark + fortress iframe + agent dispatch UI. Flashy; most of Jason’s paste was simulated — only ship pieces that are real.

**C — Mini-Vera local agent**  
Chat plans → MCP tools → summarize. Highest power, hardest on small models; needs tight tool schema + allowlist.

Recommend **A now**, skim of **C** later (slash-commands first), **B** only for dual-Ollama + Keep iframe when those endpoints are real.

## Tool / feature backlog by domain

### 1) Chat (local brain)
- Slash commands: `/health` `/vault PATH` `/kb QUERY` `/models` inject MCP then answer
- Optional “Use tools” toggle → tiny planner (≤4b) picks 1 allowlisted tool
- Clear chat / export transcript
- Persist last model choice
- System prompt presets: Vera-lite / Mechanic / Teacher
- Stop button mid-stream
- Context meter (tokens approx)

### 2) Ops / MCP (real fortress)
Already: init, health, fast sitrep, docker, gates, pipeline, git vault, vault read, kb search  
Add:
- `ollama_models` / `openclaw_models` buttons
- `morning_digest` (read-only, no vault write)
- `list_packages` / `package_summary`
- `read_repo_file` (path picker for ReClaw/Keep)
- `read_oculai` section dropdown
- `github_gap_suggestions` (read-only)
- Copy-to-clipboard on result
- Markdown render for results (not just Textbox)
- Status pill: MCP up/down last latency
- **Never** expose gated writes without confirm UI + Jason present

### 3) Models / swarm
- Refresh model list from live `/api/tags` (not hardcoded)
- Dual target: Grok VM + fortress Ollama **if** reachable (often not on host :11434 — use docker/gateway path)
- Side-by-side benchmark tab (real streams only)
- RAM warning when selecting 14b/26b on 15Gi box
- Pull/delete model helpers (dangerous — confirm)

### 4) Code coach → real coder
- Paste → explain / review / suggest patch (local)
- “Open in OpenCode” deep link / copy prompt once OpenCode installed on VM
- Diff viewer component
- Link to local repo paths under `/opt/jason-dev` if present
- Prefer fortress `qwen3-coder:30b` when dual-node works

### 5) NPC / Keep feel-alive
- Voices: Raziel, Valerie-dry, Herald (already), Scout
- Pull last N lines from Herald feed / keep-feed.json if path exists
- Bubble length cap + “one ambient line” button
- Later: async bubbles from fortress `phi4-mini` (A2 Jules work) — Gradio only displays cache

### 6) Fortress / Keep UI
- Iframe Keep when `:8130` healthy (MagicDNS + allowedHosts)
- Deep links: zombies `:8080`, reclaw dashboard `:8081`, gateway health
- Do not fake Phaser events

### 7) Files / scratch on this VM
- Browse `/workspace` / outbox
- Upload → save under `/workspace/ingest/...`
- One-click open SOLO-OPS / Ops-MCP how-to notes

### 8) RaterHub assist (you-drive)
- Checklist panel from skills (SxS 7-step, email-bill)
- Timer start/stop (local JSON) — no Hubstaff
- Guidelines snippet search (local PDF extracts)
- **No** auto-click browser from Gradio (that’s cloud/computerUse)

### 9) Shell / jobs (careful)
- Run allowlisted scripts only (ollama ps, tailscale status, curl health)
- Job log viewer
- Never free-form root shell from Gradio without hard allowlist

### 10) Polish / reliability
- Autostart systemd/user unit for Gradio
- Health page `/` shows Ollama+MCP status strip
- Dark theme polish, less emoji-dependent
- Version badge + changelog
- Crash-safe restart script in outbox
- Gradio 6 Chatbot: keep `_normalize_content` tests

## Explicit non-goals (for now)
- Fake FastMCP JSON success theater
- Fake Raziel dispatch with sleep()
- Fake CDP screenshots
- Wrong 100.64.* Tailscale map
- Full project_sitrep button (hangs)
- Unattended gated MCP writes

## Suggested ship order (if A)
1. Live model dropdown + status strip (Ollama/MCP)
2. Chat slash-commands → existing MCP helpers
3. Markdown Ops results + ollama_models / morning_digest
4. Dual-node only after fortress Ollama path proven
5. Keep iframe when :8130 up
6. OpenCode install + Code tab bridge
7. Optional mini tool-planner (C-lite)

## Success when Grok usage is gone
Jason can sitrep fortress, read vault, chat local, and coach code from one Tailscale URL with zero cloud chat.


## Priority lock (Jason 2026-09-21 ~03:04 EDT)
**Order:** Solo ops first → then coding help that edits.
Skill Hunter tab (ClawHub hunt, no auto-install) counts as solo-ops lane.

## Skill Hunter status (2026-09-21 ~03:07 EDT)
**Shipped on Gradio v2.1** as ops-lane tab: ClawHub hunt / inspect / shortlist / export handoff.
Details: `outbox/BOYD-WORKSTATION-SKILL-HUNTER.md`
Still no auto-install; full MCP `mesh-skill-hunter` remains SPECS-only until CONFIRM.

