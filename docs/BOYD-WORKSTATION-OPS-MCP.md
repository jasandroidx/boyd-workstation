# Boyd Workstation Ops/MCP (2026-09-21 ~02:57 EDT)

## Verified before wiring buttons
- `http://100.85.152.115:8100/mcp` → **400** "Client sent an HTTP request to an HTTPS server" — do not use.
- `https://100.85.152.115:8100/mcp` → TLS alert (prefer MagicDNS).
- SOT: `https://YOUR-FORTRESS-HOST/path/mcp
- Health: `https://YOUR-FORTRESS-HOST/path/mcp → 200 `reclaw-platform` streamable-http
- `initialize` → reclaw-platform 1.29.1 / protocol 2024-11-05
- `tools/call openclaw_health` → `{"ok":true,"status":"live"}`
- `tools/call stack_health` → OK (docker + APIs)
- `tools/call read_vault_file` path `Ravenstack/RAVENSTACK-OCULAI.md` → OK

## App
- File: `/workspace/ingest/gradio/boyd_workstation.py` (v2 Ops tab)
- Port **7860** (Chat/NPC/Code unchanged — local Ollama `127.0.0.1:11434`)
- **Did not** replace with Command Deck paste (fake MCP / wrong 100.64 IPs)
- Allowlist health/status + vault read + query_knowledge
- Explicitly blocks `sitrep` / `project_sitrep` / mutations

## IPs
- Grok VM: `100.97.223.55`
- Fortress: `100.85.152.115`
