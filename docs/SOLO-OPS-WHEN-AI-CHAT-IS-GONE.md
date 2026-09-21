# Solo ops when Grok Bot / cloud AI chat is gone

**Checked:** 2026-09-21 ~02:24 EDT (America/Indiana/Petersburg) — **read-only** on Grok Bot VM. No services restarted; no fortress config changes.

**Purpose:** What still works offline/local, exact URLs to open, how to start things, and concrete gaps.

---

## Quick status (this check)

| System | Status | Notes |
|--------|--------|-------|
| Gradio Boyd Workstation `:7860` | **UP** | python pid listening `0.0.0.0:7860`; file present |
| Tailscale Serve → Gradio | **UP** | MagicDNS proxy to local 7860 |
| Local Ollama `:11434` | **UP** | 12 tags; `OLLAMA_KEEP_ALIVE=30m`; `OLLAMA_MAX_LOADED_MODELS=1` |
| Tailscale peers | **OK** | `openclaw` active; `boydscomp` online |
| Fortress OpenClaw gateway `:18789` | **LIVE** (via MagicDNS) | `{"ok":true,"status":"live"}` |
| Fortress ReClaw API | **OK** | MCP health: prod 2.0.0 |
| Fortress stack (docker) | **OK** | gateway, reclaw-api, dashboard healthy |
| Fortress dashboard `:8080` by MagicDNS | **GAP** | Vite `allowedHosts` blocks hostname |
| OpenCode config/binary on this box | **MISSING** | no `~/.config/opencode/`; empty `~/.opencode/bin` |
| Fortress Ollama via host `:11434` | **NOT REACHABLE from this VM** | use fortress-local / docker path |

---

## 1) What works offline / local (no cloud AI chat needed)

- **Boyd Workstation Gradio** — Chat / NPC / Code against **local** Ollama only (`http://127.0.0.1:11434`).
- **Local Ollama** — models on this Grok Bot VM (see list below).
- **Tailscale** — reach Gradio and fortress over the tailnet without public internet AI.
- **Fortress (openclaw)** — gateway + ReClaw + dashboard containers healthy; fortress-side Ollama inventory available via stack tools.
- **RaterHub work** — browser + Rater Hub + guideline PDFs; time goes in **Workday**, not Hubstaff (see below).
- **MCP / ravenstack read tools** (when tunnel/bridge up) — health, sitrep, knowledge query — do **not** replace cloud chat quota but stay useful for ops status.

### Local Ollama models (this VM, `curl -s http://127.0.0.1:11434/api/tags`)

- `qwen3:1.7b` (default Gradio; was loaded at check — expires ~02:35 EDT under keep_alive)
- `qwen3-4b-64k:latest`, `qwen3:4b`
- `qwen2.5:7b`, `qwen2.5:7b-instruct`, `qwen2.5:14b`
- `llama3.2:1b`, `llama3.2:3b`
- `phi4-mini:latest`
- `llava-phi3:latest` / `llava-phi3:3.8b` (vision)
- `gemma4:26b` (large — RAM tight on 15 Gi box; prefer smaller for solo ops)

**Process env (observed, not changed):** `OLLAMA_HOST=0.0.0.0`, `OLLAMA_KEEP_ALIVE=30m`, `OLLAMA_MAX_LOADED_MODELS=1`.  
**RAM at check:** ~15 Gi total, ~9.8 Gi available, **no swap**.

### Fortress Ollama (via stack inventory, not this VM’s :11434)

Includes: `qwen3-coder:30b`, `qwen3-4b-64k`, `qwen3:4b`, `gpt-oss:20b-cloud`, `gemma4`, `phi4-mini`, `qwen3:1.7b` (7 listed). Prefer these **on openclaw**, not by curling `100.85.152.115:11434` from this box (connection refused).

---

## 2) Exact URLs / IPs to open

| What | URL / address |
|------|----------------|
| **Gradio (local on VM)** | `http://127.0.0.1:7860/` |
| **Gradio (Tailscale Serve / MagicDNS)** | `https://grok-bot-vm-413820329-1.tail20a090.ts.net/` |
| **This VM Tailscale IP** | `100.97.223.55` (`grok-bot-vm-413820329-1`) |
| **Fortress MagicDNS** | `openclaw.tail20a090.ts.net` → `100.85.152.115` |
| **OpenClaw gateway health** | `https://openclaw.tail20a090.ts.net:18789/health` → `{"ok":true,"status":"live"}` |
| **Dashboard by IP (works)** | `http://100.85.152.115:8080/` → HTTP 200 |
| **Dashboard by MagicDNS (broken)** | `http://openclaw.tail20a090.ts.net:8080/` → Vite host blocked (see gap) |
| **BoydsComp** | `boydscomp.tail20a090.ts.net` → `100.105.183.75` (online) |
| **Public MCP (SOT)** | `https://YOUR-FORTRESS-HOST/path/mcp |
| **Local Ollama API** | `http://127.0.0.1:11434` |

**TLS note:** Curling `https://100.85.152.115:18789/` from this box fails TLS (SNI/cert). Prefer **MagicDNS hostname** for gateway HTTPS.

**Tailscale Serve (this box):**

```
https://grok-bot-vm-413820329-1.tail20a090.ts.net (tailnet only)
|-- / proxy http://127.0.0.1:7860
```

---

## 3) How to start / check (when something is down)

### Check Ollama (local)

```bash
curl -s http://127.0.0.1:11434/api/tags | head
curl -s http://127.0.0.1:11434/api/ps   # what’s loaded + expires_at
```

Do **not** change `OLLAMA_KEEP_ALIVE` / fortress configs in a quota crunch unless you intend to.

### Start Gradio Boyd Workstation (if :7860 empty)

File: `/workspace/ingest/gradio/boyd_workstation.py`  
At check it was **already running**:

```text
/workspace/ingest/gradio/.venv/bin/python /workspace/ingest/gradio/boyd_workstation.py
```

Restart (only if needed — you asked for read-only; this is the documented start):

```bash
cd /workspace/ingest/gradio
.venv/bin/python boyd_workstation.py
# listens 0.0.0.0:7860
```

Then open local or MagicDNS URL above. Confirm Tailscale Serve still points at 7860: `tailscale serve status`.

### OpenCode on this box

**Gap:** `/home/box/.config/opencode/` does **not** exist. `/home/box/.opencode/bin/` exists but has **no** `opencode` binary.

Until installed/configured, use:

1. Gradio **Code** tab + local Ollama, or  
2. Fortress/local-coder paths on openclaw (if you use those from BoydsComp/SSH), not this stub.

### Fortress health (read-only from this box)

```bash
curl -sk https://openclaw.tail20a090.ts.net:18789/health
curl -s -o /dev/null -w '%{http_code}\n' http://100.85.152.115:8080/
tailscale status | egrep 'openclaw|boydscomp|grok-bot'
```

Or MCP (if available): `openclaw_health`, `reclaw_health`, `stack_health`, `dashboard_status`.

---

## 4) What still needs cloud vs what doesn’t

| Capability | Needs cloud AI chat / Grok Bot quota? |
|------------|----------------------------------------|
| Gradio Chat/NPC/Code via local Ollama | **No** |
| Local model inference on this VM | **No** |
| Tailscale reachability Gradio ↔ fortress ↔ BoydsComp | **No** (tailnet) |
| Fortress gateway / ReClaw / county queue / vault RAG | **No** for health & local agents (uses fortress Ollama / configured providers) |
| OpenClaw agents that call **paid/cloud** providers | **Yes** if primary routes off-box |
| Cursor / Grok Bot cloud chat itself | **Yes** — this is what’s nearly exhausted |
| RaterHub SxS rating in browser | **No** (human + Hub); AI assist optional |
| Installing/fixing OpenCode binary + config | Tooling gap on this VM — not fixed by cloud chat |
| Vite MagicDNS host allowlist on fortress dashboard | **Config gap on fortress** (needs a deliberate allowedHosts fix later — **not** done in this check) |

---

## 5) Vite `allowedHosts` note (`openclaw.tail20a090.ts.net`)

**Confirmed gap (2026-09-21):**

```text
GET http://openclaw.tail20a090.ts.net:8080/
→ Blocked request. This host ("openclaw.tail20a090.ts.net") is not allowed.
  To allow this host, add "openclaw.tail20a090.ts.net" to `server.allowedHosts` in vite.config.js.
```

**Workaround now (no config change):** open dashboard by **Tailscale IP**:

`http://100.85.152.115:8080/`

Vault memory notes an older patch (`allowedHosts: true` on OpenClaw Office) — current `:8080` dashboard still rejects MagicDNS Host. Fix later on fortress (vite.config) when you’re ready to change configs; **out of scope for this read-only pass**.

---

## 6) Workday for RaterHub time (not Hubstaff)

- Log Telus / Google **Rater Hub** hours in **Workday**.
- **Do not** use Hubstaff for that time.
- Rater workflow notes live under `/workspace/raterhub/telus/` (SxS Workflow OS). AI assist is optional; Hub itself does not require Grok Bot quota.

---

## 7) Concrete gaps checklist

1. **OpenCode missing** on Grok Bot VM (`~/.config/opencode/` absent; no binary under `~/.opencode/bin`).
2. **Vite allowedHosts** blocks MagicDNS for dashboard `:8080` — use IP until patched.
3. **Gateway HTTPS by raw IP** fails TLS — use `openclaw.tail20a090.ts.net`.
4. **Fortress Ollama not exposed** on `100.85.152.115:11434` from this VM (expected if bound to docker/host-only).
5. **MCP tunnel unit inactive** (bridge active) — public MCP URL exists; tunnel status is a soft gap for some remote clients.
6. **RAM / single loaded model** — `OLLAMA_MAX_LOADED_MODELS=1` + 15 Gi / no swap → avoid casually loading `gemma4:26b` on this VM while Gradio is hot.
7. **Cloud Grok Bot chat quota** — nearly gone; lean on Gradio + local/fortress Ollama + browser RaterHub + Workday.

---

## Peer snapshot (`tailscale status` short)

- `100.97.223.55` **grok-bot-vm-413820329-1** — this box  
- `100.85.152.115` **openclaw** — active  
- `100.105.183.75` **boydscomp** — online  
- `100.72.8.84` airavenstack  
- Older `grok-bot-vm-413820329` (`100.124.3.68`) — offline (~1d)

---

*Draft generated for solo ops. Path: `/workspace/outbox/SOLO-OPS-WHEN-AI-CHAT-IS-GONE.md`*
