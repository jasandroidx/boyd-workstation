# Survival card — when Grok / Vera chat is gone

**Repo:** https://github.com/jasandroidx/boyd-workstation  
**Date stamped:** 2026-09-21

## Open this

| What | Where |
|------|--------|
| Boyd Workstation (Gradio) | `https://grok-bot-vm-413820329-1.tail20a090.ts.net/` (Tailscale Serve → `:7860`) |
| Or local on VM | `http://127.0.0.1:7860/` |
| This repo | `git clone https://github.com/jasandroidx/boyd-workstation.git` |
| Fortress (Tailscale) | `openclaw.tail20a090.ts.net` → `100.85.152.115` |
| Grok Bot VM | `100.97.223.55` |

## After a VM wipe

```bash
git clone https://github.com/jasandroidx/boyd-workstation.git
cd boyd-workstation
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env — set MCP_URL / MCP_HEALTH_URL from your private notes (never commit)
python boyd_workstation.py
# optional: tailscale serve --bg 7860
```

Ollama models are **not** in git — re-pull: `qwen3:4b`, `phi4-mini`, `qwen2.5:7b-instruct`, etc.

## Tabs

- **Chat / NPC / Code** — local Ollama (★ recommended models per tab)
- **Ops / MCP** — needs `MCP_URL` in `.env`
- **Skill Hunter** — ClawHub search; never auto-installs

## Docs in this folder

- `SURVIVAL.md` — this card
- `PERCHANCE-PIPELINE-SCHEMATIC.md` — stills pipeline (no public API)
- `SOLO-OPS-WHEN-AI-CHAT-IS-GONE.md` — broader stack notes (scrubbed)
- `BOYD-WORKSTATION-OPS-MCP.md` — Ops tab
- `BOYD-WORKSTATION-SKILL-HUNTER.md` — Skill Hunter
- `BOYD-WORKSTATION-UPGRADE-BRAINSTORM.md` — upgrade backlog (solo ops → code)

## Do not commit

`.env`, `.venv`, `skill-hunter-shortlist.json`, Ollama weights, Funnel MCP path secrets.

## Next when Jason is back

1. Stills tab v0 (copy prompt) on Gradio  
2. Live model list from `/api/tags`  
3. Chat slash-commands → MCP  
4. Then OpenCode / coding lane  

— Vera, 2026-09-21
