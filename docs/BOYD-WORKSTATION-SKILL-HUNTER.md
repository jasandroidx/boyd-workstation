# Boyd Workstation — Skill Hunter (ops lane)

**Shipped:** 2026-09-21 ~03:07 EDT · **Author:** Vera (executor)  
**Priority lock:** Solo ops first; Skill Hunter counts as ops lane. No OpenCode / Code-tab work in this pass.

## What it is
New Gradio tab **Skill Hunter** on Boyd Workstation (`:7860`):

| Action | Behavior |
|--------|----------|
| **Hunt** | `GET https://clawhub.ai/api/v1/search?q=…&nonSuspiciousOnly=true` |
| **Trending** | `GET /api/v1/skills?sort=trending&nonSuspiciousOnly=true` |
| **Inspect** | `GET /api/v1/skills/{slug}?ownerHandle=…` — summary + SKILL.md preview |
| **Shortlist** | Local JSON only: `/workspace/ingest/gradio/skill-hunter-shortlist.json` |
| **Export handoff** | Writes `/workspace/outbox/SKILL-HUNTER-HANDOFF-*.md` for Claude Code / Jason |

**Never installs.** No Funnel recommend. Soft mesh-fit score is display-only.

## App
- File: `/workspace/ingest/gradio/boyd_workstation.py` (v2.1)
- Backup: `boyd_workstation.py.bak-before-skill-hunter-030512`
- Process: pid in `/tmp/boyd-workstation.pid` · log `/tmp/boyd-workstation.log`
- Tailscale Serve → same Gradio URL as before

## Smoke (verified this ship)
- `hunt("calendar")` → ClawHub hits with canonical `owner/slug` links
- Inspect `haidiantoutou/calendar` → version + description preview
- Shortlist add/remove persists to JSON
- Gradio `/config` includes tab label `Skill Hunter`

## Explicit non-goals (this task)
- OpenCode install / Code-tab bridge
- Auto `openclaw skills install`
- Full mesh-skill-hunter MCP server (still SPECS in radar addendum D until Jason `CONFIRM mesh-skill-hunter`)
- Dual-node / Command Deck theater

## How Jason uses it
1. Open Gradio → **Skill Hunter**
2. Hunt a goal → copy `owner/slug`
3. Inspect → Add shortlist (optional note)
4. Export handoff → paste into Claude Code on fortress only after he types CONFIRM for specific refs
