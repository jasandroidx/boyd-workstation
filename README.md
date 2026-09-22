# Boyd Workstation

Local Gradio shell for Jason Boyd’s Grok Bot VM: **Chat / NPC / Code / Ops·MCP / Prompt Brain / Skill Hunter**.

Runs against **local Ollama** (no cloud chat quota). Ops talks to a ReClaw/Ravenstack MCP URL you configure. Skill Hunter searches [ClawHub](https://clawhub.ai) and **never auto-installs**.

## Start here if chat is dead

Read **[docs/SURVIVAL.md](docs/SURVIVAL.md)** — URLs, restore steps, tab map, next builds.

## Why this repo exists

The live copy historically lived under `/workspace/ingest/gradio/` on the Grok Bot VM. That path can vanish on a computer reset. **This GitHub repo is the source of truth** — clone it back onto the VM (or anywhere with Tailscale + Ollama).

## Quick start

```bash
git clone https://github.com/jasandroidx/boyd-workstation.git
cd boyd-workstation
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Ollama must already be running locally
export OLLAMA_HOST=127.0.0.1:11434   # optional

# Optional Ops tab
cp .env.example .env   # edit MCP_URL / MCP_HEALTH_URL
set -a && source .env && set +a

python boyd_workstation.py
# → http://127.0.0.1:7860  (share=False)
```

Tailscale Serve example (private to your tailnet):

```bash
tailscale serve --bg 7860
```

## Tabs

| Tab | Uses | Notes |
|-----|------|--------|
| Chat | Local Ollama | ★ recommended: `qwen3:4b` · Dynamic model discovery & Quick Presets |
| NPC | Local Ollama | ★ recommended: `phi4-mini:latest` · Dynamic model discovery |
| Code | Local Ollama | ★ recommended: `qwen2.5:7b-instruct` · Coding presets & Outbox Export |
| Ops / MCP | MCP HTTPS | Read-only allowlist; set `MCP_URL` · Output Export |
| Prompt Brain | Local Ollama | Perchance-style image prompt expander & Outbox Export |
| Skill Hunter | ClawHub public API | Hunt / shortlist / export — **no install** |

## Features & Additions

- **🔄 Live Ollama Model Discovery:** Click *Refresh Models* in Chat, NPC, Code, or Prompt Brain tabs to dynamically query local Ollama (`/api/tags`) and list any pulled model.
- **⚡ Quick Prompt & Coding Presets:** Select preset templates for common coding workflows (Pytest generation, Security audit, Refactor, Type hints) or chat workflows (3-bullet summary, Action plan, ELI5).
- **💾 Session Outbox Export:** Export chat & code conversation histories or expanded image prompts directly to `/workspace/outbox/*.md` with one click.

## Models

Ollama models are **not** in this repo (too large). Pull what you need on the machine, e.g.:

```bash
ollama pull qwen3:4b
ollama pull phi4-mini
ollama pull qwen2.5:7b-instruct
```

## Safety

- `share=False` — do not expose Gradio to the open internet
- Never commit real `MCP_URL` Funnel paths
- Skill Hunter never installs OpenClaw skills; export handoff only
- Ops blocks gated mutation tools and hanging `project_sitrep`

## License

Private-use / Jason Boyd — public mirror for backup and sharing. No warranty.
