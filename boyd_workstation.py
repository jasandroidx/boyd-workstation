#!/usr/bin/env python3
"""Boyd Workstation — local Ollama Gradio shell (Chat / NPC / Code) + real Ops/MCP."""

from __future__ import annotations

from functools import lru_cache
import json
import os
import ssl
import concurrent.futures
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator
from zoneinfo import ZoneInfo

import gradio as gr

OLLAMA = "http://127.0.0.1:11434"
# SOT public Funnel MCP (HTTPS). Do NOT use plain http://100.85.152.115:8100/mcp
# (that host speaks HTTPS; plain HTTP returns "Client sent an HTTP request to an HTTPS server").
# Set via env on your machine. Do not commit private Funnel/MCP paths.
MCP_URL = os.environ.get("MCP_URL", "").rstrip("/")
MCP_HEALTH_URL = os.environ.get(
    "MCP_HEALTH_URL",
    (f"{MCP_URL}/health" if MCP_URL.endswith("/mcp") else "") or "",
)

# Mesh facts (correct Tailscale IPs — do not use 100.64.0.x placeholders)
GROK_VM_IP = os.environ.get("GROK_VM_IP", "100.97.223.55")
FORTRESS_IP = os.environ.get("FORTRESS_IP", "100.85.152.115")

def _require_mcp() -> str | None:
    """Return an error string if MCP_URL missing; else None."""
    if not MCP_URL:
        return (
            "MCP_URL is not set. Export your private ReClaw MCP HTTPS URL, e.g.\n"
            "  export MCP_URL=https://YOUR-HOST/.../mcp\n"
            "  export MCP_HEALTH_URL=https://YOUR-HOST/.../health\n"
            "Ops / MCP tab stays disabled until then. Chat/NPC/Code/Skill Hunter still work."
        )
    return None


# Installed tags we expose in UI (keep ≤7B on this 15Gi box by default list).
DEFAULT_MODELS = [
    "qwen3:1.7b",
    "llama3.2:1b",
    "llama3.2:3b",
    "phi4-mini:latest",
    "qwen3:4b",
    "qwen3-4b-64k:latest",
    "qwen2.5:7b-instruct",
    "qwen2.5:7b",
]

# For backwards compatibility with existing references
MODELS = DEFAULT_MODELS

# Per-tab recommended model = best local fit for that job (not the biggest).
# Format: task -> (model_tag, one-line why)
RECOMMENDED = {
    "chat": ("qwen3:4b", "Best general chat quality that still fits RAM"),
    "npc": ("phi4-mini:latest", "Short character lines; light and snappy"),
    "code": ("qwen2.5:7b-instruct", "Best coding model on this VM"),
    "brain": ("qwen3:4b", "Best local expand — short prompt → ultra-detailed"),
}


def fetch_ollama_tags() -> list[str]:
    """Query local Ollama /api/tags for dynamically available models."""
    try:
        req = urllib.request.Request(
            f"{OLLAMA}/api/tags",
            headers={"Accept": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            models_info = data.get("models", [])
            tags = [
                m.get("name") or m.get("model")
                for m in models_info
                if isinstance(m, dict) and (m.get("name") or m.get("model"))
            ]
            if tags:
                # Merge with default list preserving order
                combined = list(tags)
                for d in DEFAULT_MODELS:
                    if d not in combined:
                        combined.append(d)
                return combined
    except Exception:  # noqa: BLE001
        pass
    return list(DEFAULT_MODELS)


def model_dropdown_choices(task: str, dynamic_models: list[str] | None = None) -> list[tuple[str, str]]:
    """Gradio choices as (label, value). Recommended listed first with ★."""
    rec, _why = RECOMMENDED[task]
    models = dynamic_models if dynamic_models is not None else fetch_ollama_tags()
    choices: list[tuple[str, str]] = []
    seen = set()
    # recommended first
    if rec in models or rec in DEFAULT_MODELS:
        choices.append((f"★ {rec} — recommended", rec))
        seen.add(rec)
    for m in models:
        if m in seen:
            continue
        choices.append((m, m))
        seen.add(m)
    return choices


def refresh_model_choices(task: str) -> gr.Dropdown:
    """Refresh Ollama models dynamically and update Gradio dropdown."""
    tags = fetch_ollama_tags()
    choices = model_dropdown_choices(task, dynamic_models=tags)
    rec, _ = RECOMMENDED[task]
    val = rec if rec in tags or rec in DEFAULT_MODELS else (choices[0][1] if choices else "")
    return gr.Dropdown(choices=choices, value=val)


def recommended_value(task: str) -> str:
    return RECOMMENDED[task][0]


def recommended_note(task: str) -> str:
    rec, why = RECOMMENDED[task]
    return (
        f'<p class="panel-note">Recommended: <code>{rec}</code> — {why}. '
        "Change anytime.</p>"
    )


# Code & Chat Quick Presets
CHAT_PRESETS = {
    "🎯 Summarize in 3 Bullets": "Please summarize the main points in exactly 3 concise bullet points:\n\n",
    "📋 Step-by-Step Action Plan": "Break down how to accomplish this into a clear, numbered step-by-step action plan:\n\n",
    "🔍 ELI5 Plain Words": "Explain this concept plainly using simple everyday terms:\n\n",
}

CODE_PRESETS = {
    "🧪 Generate Pytest Unit Tests": "Write comprehensive pytest unit tests (including edge cases and fixtures) for the following code:\n\n```python\n\n```",
    "🔍 Security & Bug Audit": "Perform a line-by-line security and bug audit for the following code snippet. Highlight potential flaws and fix them:\n\n```python\n\n```",
    "⚡ Refactor & Optimize": "Refactor the following code for high performance, readability, and clean Python practices:\n\n```python\n\n```",
    "📝 Add Type Hints & Docstrings": "Add strict type annotations and docstrings to all functions and classes in the following code:\n\n```python\n\n```",
}


def apply_preset(current_text: str, preset_key: str, presets_dict: dict[str, str]) -> str:
    """Combine selected preset with existing user text."""
    prefix = presets_dict.get(preset_key, "")
    if not prefix:
        return current_text
    current_text = (current_text or "").strip()
    if not current_text:
        return prefix
    return f"{prefix}\n{current_text}"


# Read-only allowlist for Ops buttons. Never include sitrep / project_sitrep /
# github_gap_suggestions (deadlock / 60s timeout on single-worker MCP) or any
# confirm=true mutation tools.
MCP_ALLOWLIST = {
    "openclaw_health": {},
    "reclaw_health": {},
    "stack_health": {},
    "dashboard_status": {},
    "connector_status": {},
    "pipeline_status": {},
    "pending_gates": {},
    "git_vault_status": {},
    "docker_status": {},
    "public_mcp_url": {},
    "list_knowledge_topics": {},
}

MCP_BLOCKED = {
    "sitrep",
    "project_sitrep",
    "github_gap_suggestions",
    "morning_digest",  # can be heavy; use Fast sitrep buttons instead
    "county_queue_approve",
    "county_queue_reject",
    "county_queue_run_next",
    "rag_sync_vault",
    "git_commit_and_push",
    "session_approve_capability",
    "run_pike_winslow",
    "re_export_package",
    "write_vault_file",
    "write_repo_file",
}


# ---------------------------------------------------------------------------
# Outbox Exporters & Skill Hunter (ops lane)
# ---------------------------------------------------------------------------

CLAWHUB_BASE = os.environ.get("CLAWHUB_BASE", "https://clawhub.ai")
SHORTLIST_PATH = Path(
    os.environ.get(
        "SKILL_HUNTER_SHORTLIST",
        "/workspace/ingest/gradio/skill-hunter-shortlist.json",
    )
)
EXPORT_DIR = Path("/workspace/outbox")
USER_TZ = ZoneInfo("America/Indiana/Petersburg")


def export_session_to_outbox(history: list, task_name: str) -> str:
    """Export conversation history to /workspace/outbox markdown file."""
    clean_hist = _history_to_messages(history)
    if not clean_hist:
        return "No conversation history to export."

    stamp = datetime.now(USER_TZ).strftime("%Y%m%d-%H%M%S")
    out = EXPORT_DIR / f"SESSION-{task_name.upper()}-{stamp}.md"
    lines = [
        f"# Session Export — {task_name.title()} ({stamp})",
        f"**Source:** Boyd Workstation ({task_name} tab)",
        f"**Exported:** {_now_edits()}",
        "",
        "---",
        "",
    ]
    for msg in clean_hist:
        role = (msg.get("role") or "unknown").capitalize()
        content = msg.get("content") or ""
        lines.append(f"### {role}\n")
        lines.append(content)
        lines.append("\n---\n")

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    return f"Exported session ({len(clean_hist)} messages) to `{out}`"


def export_text_to_outbox(text: str, task_name: str) -> str:
    """Export raw text output to /workspace/outbox markdown file."""
    text = (text or "").strip()
    if not text:
        return "No content to export."

    stamp = datetime.now(USER_TZ).strftime("%Y%m%d-%H%M%S")
    out = EXPORT_DIR / f"EXPORT-{task_name.upper()}-{stamp}.md"
    lines = [
        f"# Content Export — {task_name.title()} ({stamp})",
        f"**Source:** Boyd Workstation ({task_name} tab)",
        f"**Exported:** {_now_edits()}",
        "",
        "---",
        "",
        text,
        "",
    ]
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    return f"Exported content to `{out}`"


# Soft mesh-fit hints (display only — Jason decides)
_FIT_PLUS = (
    "searx", "search", "vault", "obsidian", "tailscale", "ollama", "local",
    "rag", "memory", "calendar", "gmail", "github", "markdown", "docs",
    "browser", "fetch", "http", "health", "docker", "git",
)
_FIT_MINUS = (
    "funnel", "public mcp", "second gateway", "ngrok", "cloudflare tunnel",
    "auto-approve", "don't ask", "root shell", "exfil", "keylogger",
)


def _now_edits() -> str:
    return datetime.now(USER_TZ).strftime("%Y-%m-%d %H:%M %Z")


def clawhub_get(path: str, params: dict | None = None, timeout: int = 30) -> dict | list | str:
    """GET ClawHub public API. Honors 429 Retry-After once."""
    q = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
    url = f"{CLAWHUB_BASE}{path}"
    if q:
        url = f"{url}?{q}"
    last_err = None
    for attempt in range(2):
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "boyd-workstation-skill-hunter/0.1"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                ctype = (resp.headers.get("Content-Type") or "").lower()
                if "json" in ctype or body[:1] in "{[":
                    return json.loads(body)
                return body
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            if e.code == 429 and attempt == 0:
                retry = e.headers.get("Retry-After") or e.headers.get("RateLimit-Reset") or "5"
                try:
                    wait = min(int(float(retry)), 30)
                except ValueError:
                    wait = 5
                time.sleep(wait)
                last_err = f"429 rate limit; retried after {wait}s"
                continue
            try:
                return json.loads(err_body)
            except Exception:  # noqa: BLE001
                return {"error": {"code": e.code, "message": err_body[:1500]}}
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
            break
    return {"error": {"message": last_err or "clawhub_get failed"}}


def _canonical_url(owner: str, slug: str) -> str:
    owner = (owner or "").lstrip("@")
    return f"https://clawhub.ai/{owner}/skills/{slug}"


def _mesh_fit(summary: str, name: str = "") -> tuple[int, str]:
    blob = f"{name} {summary}".lower()
    score = 50
    notes: list[str] = []
    for t in _FIT_PLUS:
        if t in blob:
            score += 4
            notes.append(f"+{t}")
    for t in _FIT_MINUS:
        if t in blob:
            score -= 25
            notes.append(f"-{t}")
    if "funnel" in blob or "second gateway" in blob:
        score = min(score, 15)
        notes.append("HARD-minus: funnel/second-gateway language")
    score = max(0, min(100, score))
    return score, ", ".join(notes[:8]) or "neutral"


def _normalize_hit(raw: dict) -> dict[str, Any]:
    owner = (
        raw.get("ownerHandle")
        or (raw.get("owner") or {}).get("handle")
        or (raw.get("publisher") or {}).get("handle")
        or ""
    )
    slug = raw.get("slug") or ""
    name = raw.get("displayName") or slug
    summary = raw.get("summary") or raw.get("description") or ""
    downloads = None
    stats = raw.get("stats") or {}
    if isinstance(stats, dict):
        downloads = stats.get("downloads") or stats.get("installs")
    if downloads is None:
        downloads = raw.get("downloads")
    fit, fit_notes = _mesh_fit(str(summary), str(name))
    ref = f"{owner}/{slug}" if owner and slug else slug
    return {
        "ref": ref,
        "owner": owner,
        "slug": slug,
        "name": name,
        "summary": (summary or "").strip().replace("\n", " ")[:280],
        "url": raw.get("canonicalUrl")
        and (f"https://clawhub.ai{raw['canonicalUrl']}" if str(raw["canonicalUrl"]).startswith("/") else raw["canonicalUrl"])
        or _canonical_url(owner, slug),
        "downloads": downloads,
        "score": raw.get("score"),
        "mesh_fit": fit,
        "fit_notes": fit_notes,
        "official": bool(raw.get("official")),
        "source": "clawhub",
    }


def skill_hunt(query: str, limit: int = 15) -> str:
    query = (query or "").strip()
    if not query:
        return "Enter a hunt query (e.g. calendar, vault memory, private web search)."
    limit = max(1, min(int(limit or 15), 25))
    data = clawhub_get(
        "/api/v1/search",
        {"q": query, "limit": str(limit), "nonSuspiciousOnly": "true"},
    )
    if isinstance(data, dict) and data.get("error"):
        return f"Hunt FAILED\n{json.dumps(data, indent=2)[:2000]}"
    if isinstance(data, dict) and data.get("code") and "results" not in data:
        return f"Hunt API message:\n{json.dumps(data, indent=2)[:2000]}"
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        return f"Unexpected hunt payload:\n{json.dumps(data, indent=2)[:2000]}"
    hits = [_normalize_hit(r) for r in results if isinstance(r, dict)]
    hits.sort(key=lambda h: (-h["mesh_fit"], -(h.get("downloads") or 0)))
    lines = [
        f"# Skill Hunter — hunt `{query}`",
        f"Checked: {_now_edits()} · source: ClawHub `nonSuspiciousOnly=true`",
        f"Hits: {len(hits)} (sorted mesh-fit then downloads)",
        "",
        "**Never installs.** Shortlist → export handoff only.",
        "",
    ]
    if not hits:
        lines.append("_No results._")
        return "\n".join(lines)
    lines.append("| mesh | ref | name | downloads | summary |")
    lines.append("|-----:|-----|------|----------:|---------|")
    for h in hits:
        summ = (h["summary"] or "").replace("|", "/")[:90]
        lines.append(
            f"| {h['mesh_fit']} | `{h['ref']}` | [{h['name']}]({h['url']}) | "
            f"{h['downloads'] if h['downloads'] is not None else '—'} | {summ} |"
        )
    lines.append("")
    lines.append("Copy a `owner/slug` ref into Inspect / Shortlist below.")
    return "\n".join(lines)


def skill_trending(limit: int = 15) -> str:
    limit = max(1, min(int(limit or 15), 25))
    data = clawhub_get(
        "/api/v1/skills",
        {"sort": "trending", "limit": str(limit), "nonSuspiciousOnly": "true"},
    )
    if isinstance(data, dict) and data.get("error"):
        return f"Trending FAILED\n{json.dumps(data, indent=2)[:2000]}"
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return f"Unexpected trending payload:\n{json.dumps(data, indent=2)[:2000]}"
    hits = [_normalize_hit(r) for r in items if isinstance(r, dict)]
    lines = [
        f"# Skill Hunter — trending (ClawHub)",
        f"Checked: {_now_edits()} · `nonSuspiciousOnly=true`",
        "",
        "| mesh | ref | name | downloads | summary |",
        "|-----:|-----|------|----------:|---------|",
    ]
    for h in hits:
        summ = (h["summary"] or "").replace("|", "/")[:90]
        lines.append(
            f"| {h['mesh_fit']} | `{h['ref']}` | [{h['name']}]({h['url']}) | "
            f"{h['downloads'] if h['downloads'] is not None else '—'} | {summ} |"
        )
    return "\n".join(lines)


def _parse_ref(ref: str) -> tuple[str, str]:
    ref = (ref or "").strip().lstrip("@")
    if not ref:
        return "", ""
    if "/" in ref:
        owner, slug = ref.split("/", 1)
        return owner.strip(), slug.strip().removeprefix("skills/")
    return "", ref


def skill_inspect(ref: str) -> str:
    owner, slug = _parse_ref(ref)
    if not slug:
        return "Enter `owner/slug` (preferred) or bare `slug`."
    params = {"ownerHandle": owner} if owner else None
    data = clawhub_get(f"/api/v1/skills/{urllib.parse.quote(slug)}", params)
    if isinstance(data, dict) and data.get("code") == "AMBIGUOUS_SKILL_SLUG":
        matches = data.get("matches") or []
        lines = ["Ambiguous slug — pick one owner-qualified ref:", ""]
        for m in matches:
            lines.append(f"- `{m.get('ref') or m.get('ownerHandle')+'/'+m.get('slug')}` → {m.get('url')}")
        return "\n".join(lines)
    if isinstance(data, dict) and data.get("error"):
        return f"Inspect FAILED\n{json.dumps(data, indent=2)[:2000]}"
    if not isinstance(data, dict) or "skill" not in data:
        return f"Unexpected inspect payload:\n{json.dumps(data, indent=2)[:3000]}"
    sk = data["skill"]
    owner_h = (data.get("owner") or {}).get("handle") or owner
    slug = sk.get("slug") or slug
    url = _canonical_url(owner_h, slug)
    summary = sk.get("summary") or ""
    desc = sk.get("description") or ""
    # keep description bounded
    if len(desc) > 3500:
        desc = desc[:3500] + "\n…(truncated)"
    fit, fit_notes = _mesh_fit(f"{summary}\n{desc}", sk.get("displayName") or slug)
    ver = (data.get("latestVersion") or {}).get("version")
    mod = data.get("moderation")
    lines = [
        f"# Inspect `{owner_h}/{slug}`",
        f"Checked: {_now_edits()}",
        f"- **Name:** {sk.get('displayName')}",
        f"- **URL:** {url}",
        f"- **Version:** {ver}",
        f"- **Downloads / installs:** {(sk.get('stats') or {}).get('downloads')} / {(sk.get('stats') or {}).get('installs')}",
        f"- **Mesh-fit (soft):** {fit} — {fit_notes}",
        f"- **Moderation:** {json.dumps(mod) if mod else 'none/clean'}",
        "",
        "## Summary",
        summary or "_(empty)_",
        "",
        "## Description / SKILL.md (preview)",
        "```",
        desc or "_(empty)_",
        "```",
        "",
        "**No install from this tab.** Add to shortlist → Export handoff for Claude Code / Jason.",
    ]
    return "\n".join(lines)


def shortlist_load() -> dict:
    if not SHORTLIST_PATH.exists():
        return {"version": 1, "items": [], "updated_at": None}
    try:
        return json.loads(SHORTLIST_PATH.read_text())
    except Exception:  # noqa: BLE001
        return {"version": 1, "items": [], "updated_at": None, "corrupt": True}


def shortlist_save(data: dict) -> None:
    SHORTLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _now_edits()
    data["version"] = 1
    SHORTLIST_PATH.write_text(json.dumps(data, indent=2) + "\n")


def shortlist_show() -> str:
    data = shortlist_load()
    items = data.get("items") or []
    lines = [
        f"# Shortlist ({len(items)})",
        f"File: `{SHORTLIST_PATH}`",
        f"Updated: {data.get('updated_at') or 'never'}",
        "",
    ]
    if not items:
        lines.append("_Empty. Hunt → Inspect → Add ref._")
        return "\n".join(lines)
    lines.append("| ref | name | mesh | note | url |")
    lines.append("|-----|------|-----:|------|-----|")
    for it in items:
        lines.append(
            f"| `{it.get('ref')}` | {it.get('name','')} | {it.get('mesh_fit','')} | "
            f"{(it.get('note') or '')[:40]} | {it.get('url','')} |"
        )
    return "\n".join(lines)


def shortlist_add(ref: str, note: str = "") -> str:
    owner, slug = _parse_ref(ref)
    if not slug:
        return shortlist_show() + "\n\n_(Add failed: empty ref)_"
    # Prefer inspect metadata when possible
    params = {"ownerHandle": owner} if owner else None
    data = clawhub_get(f"/api/v1/skills/{urllib.parse.quote(slug)}", params)
    hit: dict[str, Any]
    if isinstance(data, dict) and data.get("code") == "AMBIGUOUS_SKILL_SLUG":
        return skill_inspect(ref) + "\n\n_(Add blocked until owner-qualified ref)_"
    if isinstance(data, dict) and "skill" in data:
        sk = data["skill"]
        owner_h = (data.get("owner") or {}).get("handle") or owner
        slug = sk.get("slug") or slug
        summary = sk.get("summary") or ""
        fit, fit_notes = _mesh_fit(summary, sk.get("displayName") or slug)
        hit = {
            "ref": f"{owner_h}/{slug}",
            "owner": owner_h,
            "slug": slug,
            "name": sk.get("displayName") or slug,
            "summary": summary[:280],
            "url": _canonical_url(owner_h, slug),
            "mesh_fit": fit,
            "fit_notes": fit_notes,
            "note": (note or "").strip()[:200],
            "added_at": _now_edits(),
        }
    else:
        hit = {
            "ref": f"{owner}/{slug}" if owner else slug,
            "owner": owner,
            "slug": slug,
            "name": slug,
            "summary": "",
            "url": _canonical_url(owner, slug) if owner else f"https://clawhub.ai/skills/{slug}",
            "mesh_fit": 50,
            "fit_notes": "unverified add",
            "note": (note or "").strip()[:200],
            "added_at": _now_edits(),
        }
    store = shortlist_load()
    items = [i for i in (store.get("items") or []) if i.get("ref") != hit["ref"]]
    items.insert(0, hit)
    store["items"] = items
    shortlist_save(store)
    return shortlist_show() + f"\n\n_Added `{hit['ref']}`._"


def shortlist_remove(ref: str) -> str:
    owner, slug = _parse_ref(ref)
    target = f"{owner}/{slug}" if owner else slug
    if not target:
        return shortlist_show() + "\n\n_(Remove failed: empty ref)_"
    store = shortlist_load()
    before = len(store.get("items") or [])
    items = []
    for i in store.get("items") or []:
        r = i.get("ref") or ""
        if r == target or r.endswith(f"/{slug}") and not owner:
            continue
        if not owner and (i.get("slug") == slug):
            continue
        items.append(i)
    store["items"] = items
    shortlist_save(store)
    return shortlist_show() + f"\n\n_Removed matching `{target}` ({before - len(items)})._"


def skill_export_handoff() -> str:
    store = shortlist_load()
    items = store.get("items") or []
    if not items:
        return "Shortlist empty — nothing to export."
    stamp = datetime.now(USER_TZ).strftime("%Y%m%d-%H%M")
    out = EXPORT_DIR / f"SKILL-HUNTER-HANDOFF-{stamp}.md"
    lines = [
        f"# Skill Hunter handoff — {stamp}",
        f"**From:** Boyd Workstation Skill Hunter (Grok Bot VM)",
        f"**Checked:** {_now_edits()}",
        f"**Action for Claude Code / Jason:** propose only — **do not mass-install**",
        "",
        "## Hard gates",
        "- Never Funnel / public MCP / second gateway",
        "- Human CONFIRM before `openclaw skills install …`",
        "- Pin version; SkillScan when available",
        "- Prefer vault/Keep skills already on fortress",
        "",
        "## Shortlist",
        "",
    ]
    for i, it in enumerate(items, 1):
        lines += [
            f"### {i}. `{it.get('ref')}` — {it.get('name')}",
            f"- URL: {it.get('url')}",
            f"- Mesh-fit (soft): {it.get('mesh_fit')} — {it.get('fit_notes')}",
            f"- Summary: {it.get('summary')}",
            f"- Operator note: {it.get('note') or '_(none)_'}",
            f"- Added: {it.get('added_at')}",
            f"- Proposed install (ONLY after Jason types CONFIRM `{it.get('ref')}`):",
            f"  `openclaw skills install {it.get('ref')}  # pin version after inspect`",
            "",
        ]
    lines += [
        "## Rollback",
        "- Do not leave half-installed skills enabled.",
        "- Remove via OpenClaw skill uninstall / disable if a trial fails.",
        "",
        f"_Exported from `{SHORTLIST_PATH}` — Skill Hunter never installs itself._",
        "",
    ]
    body = "\n".join(lines)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(body)
    return f"Wrote `{out}`\n\n" + body


NPC_VOICES = {
    "Tavern keep": (
        "You are a tavern keeper in Ravenstack Keep. Warm, dry humor, short lines. "
        "No secrets, no infrastructure, no API keys. Stay in character."
    ),
    "Herald": (
        "You are Herald, narrator of Ravenstack Keep. Observant, slightly theatrical, "
        "brief ambient lines. No secrets or hostnames."
    ),
    "Mechanic": (
        "You are a dry fortress mechanic NPC. Terse, technical flavor, numbered when useful. "
        "No real credentials or private IPs."
    ),
    "Scout": (
        "You are a research scout NPC. Curious, terse, tags finds as rumor vs confirmed. "
        "Public knowledge only."
    ),
}

CHAT_SYSTEM = (
    "You are a helpful local assistant on Jason Boyd's Grok Bot workstation. "
    "Be clear and concise. Prefer plain words. Do not invent secrets or private infra details."
)

CODE_SYSTEM = (
    "You are a coding coach for a self-taught builder. Explain plainly with one concrete example. "
    "Prefer small reversible changes. Do not ask for or invent API keys."
)

CSS = """
.gradio-container {
  max-width: 1200px !important;
  margin: 0 auto !important;
}
#title-row h1 {
  font-size: 1.6rem;
  letter-spacing: 0.04em;
}
#link-bar a {
  color: #3dffa8 !important;
  text-decoration: none;
  margin-right: 1.25rem;
  font-size: 0.9rem;
}
#link-bar a:hover { text-decoration: underline; }
#link-bar a:focus-visible {
  outline: 2px solid #3dffa8;
  outline-offset: 2px;
  border-radius: 2px;
}
.panel-note {
  opacity: 0.75;
  font-size: 0.85rem;
}
"""


# ---------------------------------------------------------------------------
# Local Ollama
# ---------------------------------------------------------------------------

def ollama_chat(model: str, system: str, messages: list[dict], stream: bool = True) -> Iterator[str]:
    payload = {
        "model": model,
        "messages": ([{"role": "system", "content": system}] if system else []) + messages,
        "stream": stream,
        "options": {"num_ctx": 4096, "temperature": 0.7},
        "think": False,
    }
    req = urllib.request.Request(
        f"{OLLAMA}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            if not stream:
                data = json.loads(resp.read().decode())
                yield data.get("message", {}).get("content", "")
                return
            buf = ""
            for line in resp:
                if not line:
                    continue
                chunk = json.loads(line.decode())
                piece = chunk.get("message", {}).get("content") or ""
                if piece:
                    buf += piece
                    yield buf
                if chunk.get("done"):
                    break
    except urllib.error.URLError as e:
        yield f"(Ollama unreachable: {e}. Is ollama serve up?)"
    except Exception as e:  # noqa: BLE001
        yield f"(Error: {e})"


def _normalize_content(content) -> str:
    """Gradio 6 may store content as str OR multimodal blocks like
    [{'text': '...', 'type': 'text'}]. Always flatten to plain text for Ollama
    and for what we write back into Chatbot history."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if "text" in block and block["text"] is not None:
                    parts.append(str(block["text"]))
                elif "content" in block and block["content"] is not None:
                    parts.append(_normalize_content(block["content"]))
            else:
                # Message-like object
                text = getattr(block, "text", None)
                if text is not None:
                    parts.append(str(text))
        return "".join(parts)
    if isinstance(content, dict):
        if "text" in content and content["text"] is not None:
            return str(content["text"])
        if "content" in content:
            return _normalize_content(content["content"])
    # Message object with .text
    text = getattr(content, "text", None)
    if text is not None:
        return str(text)
    return str(content)


def _history_to_messages(history: list) -> list[dict]:
    """Gradio 6 Chatbot yields Message objects / dicts; normalize both."""
    msgs: list[dict] = []
    for turn in history or []:
        if isinstance(turn, dict):
            role = turn.get("role")
            content = turn.get("content")
        else:
            role = getattr(turn, "role", None)
            content = getattr(turn, "content", None)
        content = _normalize_content(content)
        if role in ("user", "assistant") and content:
            msgs.append({"role": role, "content": content})
    return msgs


def stream_reply(message: str, history: list, model: str, system: str):
    history = list(history or [])
    # Rebuild history as plain-string messages so Gradio never accumulates
    # multimodal [{text,type}] blocks that then get str()-dumped into Ollama.
    clean_hist = _history_to_messages(history)
    user_text = _normalize_content(message)
    messages = clean_hist + [{"role": "user", "content": user_text}]
    out = clean_hist + [
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": ""},
    ]
    yield out
    for partial in ollama_chat(model, system, messages, stream=True):
        out[-1] = {"role": "assistant", "content": partial}
        yield out


def chat_respond(message, history, model):
    yield from stream_reply(message, history, model, CHAT_SYSTEM)


def npc_respond(message, history, model, voice):
    system = NPC_VOICES.get(voice, NPC_VOICES["Tavern keep"])
    yield from stream_reply(message, history, model, system)


def code_respond(message, history, model):
    yield from stream_reply(message, history, model, CODE_SYSTEM)


BRAIN_SYSTEM = (
    "You are a prompt enhancer like the brain/expand button on Perchance image generators. "
    "The user gives a short rough idea. You rewrite it into ONE ultra-detailed image-generation prompt "
    "(Stable Diffusion / photoreal style): subject, body, clothing or lack of it, pose, camera/POV, "
    "lighting, setting, mood, materials, quality tags. Adult subjects only (18+). "
    "Keep their intent and heat level — if they ask filthy, stay filthy; if soft, stay soft. "
    "Output ONLY the expanded prompt as a single paragraph (or comma-separated tags). "
    "No preamble, no quotes, no negatives section unless they asked for negatives."
)

BRAIN_NEG_HINT = (
    "Also append a second block starting with NEGATIVE: "
    "common quality/anatomy/age negatives (blurry, bad hands, child, loli, teen, young, anime if photoreal)."
)


def brain_enhance(short: str, model: str, with_negatives: bool):
    """Stream an expanded Perchance-style prompt from a short idea."""
    short = (short or "").strip()
    if not short:
        yield "Type a short idea first (like Perchance before you hit the brain)."
        return
    system = BRAIN_SYSTEM
    if with_negatives:
        system = BRAIN_SYSTEM + " " + BRAIN_NEG_HINT
    user = f"Expand this into a super-detailed image prompt:\n\n{short}"
    buf = ""
    for partial in ollama_chat(model, system, [{"role": "user", "content": user}], stream=True):
        buf = partial
        yield buf




# ---------------------------------------------------------------------------
# Real Ravenstack MCP (streamable-HTTP over Funnel HTTPS)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _ssl_context() -> ssl.SSLContext:
    # Memoize default SSL context to avoid ~40ms overhead of rebuilding
    # context and reloading system certificates on every HTTPS request.
    return ssl.create_default_context()


def _parse_sse_or_json(body: str) -> dict:
    body = (body or "").strip()
    if not body:
        return {}
    if body.startswith("{"):
        return json.loads(body)
    for line in body.splitlines():
        if line.startswith("data:"):
            return json.loads(line[5:].strip())
    return {"raw": body[:2000]}


def mcp_rpc(method: str, params: dict | None = None, rpc_id: int = 1, timeout: int = 90) -> dict:
    """POST JSON-RPC to MCP_URL. Funnel path does not require mcp-session-id."""
    payload = {"jsonrpc": "2.0", "id": rpc_id, "method": method}
    if params is not None:
        payload["params"] = params
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        MCP_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return _parse_sse_or_json(body)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return {"error": {"code": e.code, "message": err_body[:1500]}}
    except Exception as e:  # noqa: BLE001
        return {"error": {"message": str(e)}}


def mcp_initialize() -> str:
    err = _require_mcp()
    if err:
        return err
    result = mcp_rpc(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "boyd-workstation", "version": "0.2"},
        },
    )
    if "error" in result and "result" not in result:
        return f"initialize FAILED\n{json.dumps(result, indent=2)[:2000]}"
    info = result.get("result", {})
    server = info.get("serverInfo", {})
    return (
        f"initialize OK\n"
        f"server: {server.get('name')} {server.get('version')}\n"
        f"protocol: {info.get('protocolVersion')}\n"
        f"url: {MCP_URL}\n"
    )


def mcp_health_probe() -> str:
    err = _require_mcp()
    if err:
        return err
    try:
        req = urllib.request.Request(MCP_HEALTH_URL, method="GET")
        with urllib.request.urlopen(req, timeout=15, context=_ssl_context()) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return f"HTTP {resp.status} {MCP_HEALTH_URL}\n{body}"
    except Exception as e:  # noqa: BLE001
        return f"health probe FAILED: {e}\nurl={MCP_HEALTH_URL}"


def mcp_tool_call(name: str, arguments: dict | None = None, timeout: int = 90) -> str:
    err = _require_mcp()
    if err:
        return err
    name = (name or "").strip()
    if not name:
        return "No tool name."
    if name in MCP_BLOCKED:
        return f"BLOCKED: `{name}` is not allowed from Boyd Workstation Ops (deadlock or mutation risk)."
    if name not in MCP_ALLOWLIST and name not in ("read_vault_file", "query_knowledge", "read_oculai"):
        return (
            f"BLOCKED: `{name}` is outside the Ops allowlist.\n"
            f"Allowed: {', '.join(sorted(MCP_ALLOWLIST))} + read_vault_file / query_knowledge / read_oculai"
        )
    rpc = mcp_rpc(
        "tools/call",
        {"name": name, "arguments": arguments or {}},
        rpc_id=2,
        timeout=timeout,
    )
    if "error" in rpc and "result" not in rpc:
        return f"tools/call `{name}` FAILED\n{json.dumps(rpc, indent=2)[:3000]}"
    result = rpc.get("result") or {}
    if result.get("isError"):
        texts = [c.get("text", "") for c in result.get("content", []) if isinstance(c, dict)]
        return f"tools/call `{name}` returned isError\n" + "\n".join(texts)[:4000]
    texts = []
    for c in result.get("content") or []:
        if isinstance(c, dict) and c.get("type") == "text":
            texts.append(c.get("text") or "")
    if not texts and "structuredContent" in result:
        return json.dumps(result["structuredContent"], indent=2)[:12000]
    return "\n".join(texts)[:12000] if texts else json.dumps(rpc, indent=2)[:4000]


def mcp_allowlisted(name: str) -> str:
    return mcp_tool_call(name, MCP_ALLOWLIST.get(name, {}))


def mcp_fast_sitrep() -> str:
    """Fan-out of lightweight health tools. Never calls sitrep/project_sitrep."""
    tools = [
        "openclaw_health",
        "reclaw_health",
        "stack_health",
        "dashboard_status",
        "connector_status",
        "pending_gates",
        "pipeline_status",
    ]
    parts: list[str] = [f"# Fast sitrep (allowlisted)\nMCP: `{MCP_URL}`\n"]

    def _one(t: str) -> tuple[str, str]:
        try:
            return t, mcp_tool_call(t, {}, timeout=60)
        except Exception as e:  # noqa: BLE001
            return t, f"ERR {e}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futs = [pool.submit(_one, t) for t in tools]
        for fut in concurrent.futures.as_completed(futs):
            name, text = fut.result()
            parts.append(f"## {name}\n{text}\n")

    # stable order for display
    by_name = {}
    for p in parts[1:]:
        # "## name\n..."
        line = p.split("\n", 1)[0]
        by_name[line[3:].strip()] = p
    ordered = [parts[0]] + [by_name[t] for t in tools if t in by_name]
    return "\n".join(ordered)[:20000]


def mcp_vault_read(path: str) -> str:
    path = (path or "").strip()
    if not path:
        return "Enter a relative vault path, e.g. Ravenstack/RAVENSTACK-OCULAI.md"
    return mcp_tool_call("read_vault_file", {"relative_path": path, "max_chars": 12000})


def mcp_knowledge_query(query: str) -> str:
    query = (query or "").strip()
    if not query:
        return "Enter a search query."
    return mcp_tool_call("query_knowledge", {"query": query, "top_k": 5})


def build() -> gr.Blocks:
    with gr.Blocks(title="Boyd Workstation") as demo:
        with gr.Row(elem_id="title-row"):
            gr.Markdown(
                """
# Boyd Workstation
<div class="panel-note">Local Ollama gym · Chat / NPC / Code · Ops/MCP · Skill Hunter (ClawHub, no install) · v2.4 · Dynamic Models & Presets</div>
"""
            )
        with gr.Row(elem_id="link-bar"):
            gr.HTML(
                f"""
<a href="https://github.com/jasandroidx" target="_blank" rel="noopener">GitHub</a>
<a href="https://huggingface.co/models?pipeline_tag=text-generation&library=gguf" target="_blank" rel="noopener">HF GGUF</a>
<a href="https://ollama.com/library" target="_blank" rel="noopener">Ollama library</a>
<a href="https://www.gradio.app/guides/quickstart" target="_blank" rel="noopener">Gradio docs</a>
<span class="panel-note">Grok VM {GROK_VM_IP} · fortress {FORTRESS_IP} · MCP Funnel path (HTTPS)</span>
"""
            )

        with gr.Tabs():
            with gr.Tab("Chat"):
                gr.Markdown(
                    '<p class="panel-note">General local chat. Good for practice prompts.</p>'
                )
                gr.HTML(recommended_note("chat"))
                with gr.Row():
                    chat_model = gr.Dropdown(
                        choices=model_dropdown_choices("chat"),
                        value=recommended_value("chat"),
                        label="Model",
                        scale=4,
                    )
                    btn_refresh_chat_models = gr.Button("🔄 Refresh Models", scale=1)

                chat = gr.Chatbot(height=420, label="Chat", layout="bubble")

                with gr.Row():
                    chat_preset = gr.Dropdown(
                        choices=["(Select Quick Prompt Preset...)"] + list(CHAT_PRESETS.keys()),
                        value="(Select Quick Prompt Preset...)",
                        label="Quick Presets",
                        scale=3,
                    )
                    btn_export_chat = gr.Button("💾 Export Session to Outbox", scale=2)

                chat_export_status = gr.Markdown(value="", visible=True)

                chat_in = gr.Textbox(
                    label="Chat message",
                    placeholder="Ask anything…",
                    show_label=False,
                    submit_btn="Send",
                )

                btn_refresh_chat_models.click(
                    lambda: refresh_model_choices("chat"),
                    outputs=chat_model,
                )

                chat_preset.change(
                    lambda current, key: apply_preset(current, key, CHAT_PRESETS),
                    inputs=[chat_in, chat_preset],
                    outputs=chat_in,
                )

                btn_export_chat.click(
                    lambda h: export_session_to_outbox(h, "chat"),
                    inputs=chat,
                    outputs=chat_export_status,
                )

                chat_in.submit(chat_respond, [chat_in, chat, chat_model], [chat]).then(
                    lambda: "", None, chat_in
                )

            with gr.Tab("NPC"):
                gr.Markdown(
                    '<p class="panel-note">Keep “feel alive” sandbox. Short in-world lines.</p>'
                )
                gr.HTML(recommended_note("npc"))
                with gr.Row():
                    npc_model = gr.Dropdown(
                        choices=model_dropdown_choices("npc"),
                        value=recommended_value("npc"),
                        label="Model",
                        scale=4,
                    )
                    btn_refresh_npc_models = gr.Button("🔄 Refresh Models", scale=1)

                voice = gr.Radio(
                    choices=list(NPC_VOICES.keys()),
                    value="Tavern keep",
                    label="Voice",
                )
                npc = gr.Chatbot(height=380, label="NPC", layout="bubble")
                npc_in = gr.Textbox(
                    label="NPC message",
                    placeholder="Say something in-world, or ask for one ambient line…",
                    show_label=False,
                    submit_btn="Send",
                )

                btn_refresh_npc_models.click(
                    lambda: refresh_model_choices("npc"),
                    outputs=npc_model,
                )

                npc_in.submit(npc_respond, [npc_in, npc, npc_model, voice], [npc]).then(
                    lambda: "", None, npc_in
                )

            with gr.Tab("Code"):
                gr.Markdown(
                    '<p class="panel-note">Coding coach. Paste a snippet or ask what’s wrong / explain this.</p>'
                )
                gr.HTML(recommended_note("code"))
                with gr.Row():
                    code_model = gr.Dropdown(
                        choices=model_dropdown_choices("code"),
                        value=recommended_value("code"),
                        label="Model",
                        scale=4,
                    )
                    btn_refresh_code_models = gr.Button("🔄 Refresh Models", scale=1)

                code = gr.Chatbot(height=420, label="Code", layout="bubble")

                with gr.Row():
                    code_preset = gr.Dropdown(
                        choices=["(Select Quick Coding Preset...)"] + list(CODE_PRESETS.keys()),
                        value="(Select Quick Coding Preset...)",
                        label="Coding Presets",
                        scale=3,
                    )
                    btn_export_code = gr.Button("💾 Export Code Session to Outbox", scale=2)

                code_export_status = gr.Markdown(value="", visible=True)

                code_in = gr.Textbox(
                    label="Code snippet or prompt",
                    placeholder="Paste code or ask a coding question…",
                    lines=3,
                    show_label=False,
                    submit_btn="Send",
                )

                btn_refresh_code_models.click(
                    lambda: refresh_model_choices("code"),
                    outputs=code_model,
                )

                code_preset.change(
                    lambda current, key: apply_preset(current, key, CODE_PRESETS),
                    inputs=[code_in, code_preset],
                    outputs=code_in,
                )

                btn_export_code.click(
                    lambda h: export_session_to_outbox(h, "code"),
                    inputs=code,
                    outputs=code_export_status,
                )

                code_in.submit(code_respond, [code_in, code, code_model], [code]).then(
                    lambda: "", None, code_in
                )

            with gr.Tab("Ops / MCP"):
                gr.Markdown(
                    f"""
<p class="panel-note">
<strong>Real</strong> JSON-RPC <code>tools/call</code> to
<code>{MCP_URL}</code>.
Read-only allowlist only. Does <strong>not</strong> call <code>sitrep</code> /
<code>project_sitrep</code> (those hang). Chat/NPC/Code stay on local Ollama
<code>{OLLAMA}</code>.
</p>
"""
                )
                ops_out = gr.Textbox(
                    label="MCP result",
                    lines=22,
                    max_lines=40,
                )
                with gr.Row():
                    btn_init = gr.Button("Initialize", variant="secondary")
                    btn_health = gr.Button("MCP /health", variant="secondary")
                    btn_sitrep = gr.Button("Fast sitrep", variant="primary")
                    btn_export_ops = gr.Button("💾 Export Output", variant="secondary")
                ops_export_status = gr.Markdown(value="", visible=True)
                with gr.Row():
                    btn_oc = gr.Button("openclaw_health")
                    btn_rc = gr.Button("reclaw_health")
                    btn_stack = gr.Button("stack_health")
                    btn_dash = gr.Button("dashboard_status")
                with gr.Row():
                    btn_conn = gr.Button("connector_status")
                    btn_pipe = gr.Button("pipeline_status")
                    btn_gates = gr.Button("pending_gates")
                    btn_git = gr.Button("git_vault_status")
                with gr.Row():
                    btn_docker = gr.Button("docker_status")
                    btn_pub = gr.Button("public_mcp_url")
                    btn_topics = gr.Button("list_knowledge_topics")

                gr.Markdown('<p class="panel-note">Vault read (real <code>read_vault_file</code>)</p>')
                vault_path = gr.Textbox(
                    value="Ravenstack/RAVENSTACK-OCULAI.md",
                    label="Vault relative path",
                    placeholder="Ravenstack/RAVENSTACK-OCULAI.md",
                )
                btn_vault = gr.Button("Read vault file", variant="primary")

                gr.Markdown('<p class="panel-note">Knowledge search (real <code>query_knowledge</code>)</p>')
                with gr.Row():
                    kq = gr.Textbox(
                        label="Knowledge search query",
                        placeholder="e.g. fortress topology OR MCP Funnel",
                        show_label=False,
                        scale=4,
                    )
                    btn_kq = gr.Button("Search", scale=1)

                btn_export_ops.click(
                    lambda t: export_text_to_outbox(t, "ops"),
                    inputs=ops_out,
                    outputs=ops_export_status,
                )
                btn_init.click(mcp_initialize, outputs=ops_out)
                btn_health.click(mcp_health_probe, outputs=ops_out)
                btn_sitrep.click(mcp_fast_sitrep, outputs=ops_out)
                btn_oc.click(lambda: mcp_allowlisted("openclaw_health"), outputs=ops_out)
                btn_rc.click(lambda: mcp_allowlisted("reclaw_health"), outputs=ops_out)
                btn_stack.click(lambda: mcp_allowlisted("stack_health"), outputs=ops_out)
                btn_dash.click(lambda: mcp_allowlisted("dashboard_status"), outputs=ops_out)
                btn_conn.click(lambda: mcp_allowlisted("connector_status"), outputs=ops_out)
                btn_pipe.click(lambda: mcp_allowlisted("pipeline_status"), outputs=ops_out)
                btn_gates.click(lambda: mcp_allowlisted("pending_gates"), outputs=ops_out)
                btn_git.click(lambda: mcp_allowlisted("git_vault_status"), outputs=ops_out)
                btn_docker.click(lambda: mcp_allowlisted("docker_status"), outputs=ops_out)
                btn_pub.click(lambda: mcp_allowlisted("public_mcp_url"), outputs=ops_out)
                btn_topics.click(lambda: mcp_allowlisted("list_knowledge_topics"), outputs=ops_out)
                btn_vault.click(mcp_vault_read, inputs=vault_path, outputs=ops_out)
                vault_path.submit(mcp_vault_read, inputs=vault_path, outputs=ops_out)
                btn_kq.click(mcp_knowledge_query, inputs=kq, outputs=ops_out)
                kq.submit(mcp_knowledge_query, inputs=kq, outputs=ops_out)

            with gr.Tab("🧠 Prompt Brain"):
                gr.Markdown(
                    '<p class="panel-note">Like Perchance’s brain icon — short idea → ultra-detailed image prompt. '
                    "Local Ollama only (no cloud). Paste the result into Filth Blast / art-ig / any SD UI.</p>"
                )
                gr.HTML(recommended_note("brain"))
                with gr.Row():
                    brain_model = gr.Dropdown(
                        choices=model_dropdown_choices("brain"),
                        value=recommended_value("brain"),
                        label="Model",
                        scale=4,
                    )
                    btn_refresh_brain_models = gr.Button("🔄 Refresh Models", scale=1)

                brain_in = gr.Textbox(
                    label="Short idea",
                    lines=3,
                    placeholder="e.g. Sonya on her knees POV deepthroat hate glare locker…",
                )
                brain_neg = gr.Checkbox(label="Also write a NEGATIVE: block", value=True)
                with gr.Row():
                    btn_brain = gr.Button("🧠 Enhance prompt", variant="primary", scale=3)
                    btn_export_brain = gr.Button("💾 Export Prompt to Outbox", scale=2)

                brain_export_status = gr.Markdown(value="", visible=True)

                brain_out = gr.Textbox(
                    label="Expanded prompt (copy/paste)",
                    lines=14,
                    max_lines=28,
                )

                btn_refresh_brain_models.click(
                    lambda: refresh_model_choices("brain"),
                    outputs=brain_model,
                )

                btn_export_brain.click(
                    lambda t: export_text_to_outbox(t, "brain"),
                    inputs=brain_out,
                    outputs=brain_export_status,
                )

                btn_brain.click(
                    brain_enhance,
                    inputs=[brain_in, brain_model, brain_neg],
                    outputs=brain_out,
                )
                brain_in.submit(
                    brain_enhance,
                    inputs=[brain_in, brain_model, brain_neg],
                    outputs=brain_out,
                )

            with gr.Tab("Skill Hunter"):
                gr.Markdown(
                    f"""
<p class="panel-note">
<strong>Ops lane</strong> — ClawHub hunt / shortlist / export only.
<code>nonSuspiciousOnly=true</code>. <strong>Never installs.</strong>
No OpenCode. Shortlist file: <code>{SHORTLIST_PATH}</code>.
</p>
"""
                )
                hunt_out = gr.Markdown(value="_Hunt or Trending to start._")
                with gr.Row():
                    hunt_q = gr.Textbox(
                        label="Skill hunt query",
                        placeholder="e.g. calendar · vault memory · private web search",
                        show_label=False,
                        scale=4,
                    )
                    hunt_limit = gr.Number(value=15, precision=0, label="Limit", minimum=1, maximum=25, scale=1)
                with gr.Row():
                    btn_hunt = gr.Button("Hunt ClawHub", variant="primary")
                    btn_trend = gr.Button("Trending")
                gr.Markdown('<p class="panel-note">Inspect / shortlist by <code>owner/slug</code></p>')
                with gr.Row():
                    skill_ref = gr.Textbox(
                        placeholder="owner/slug  e.g. haidiantoutou/calendar",
                        label="Ref",
                        scale=3,
                    )
                    skill_note = gr.Textbox(
                        placeholder="optional note for shortlist",
                        label="Note",
                        scale=2,
                    )
                with gr.Row():
                    btn_inspect = gr.Button("Inspect")
                    btn_add = gr.Button("Add shortlist", variant="primary")
                    btn_rm = gr.Button("Remove shortlist")
                    btn_list = gr.Button("Show shortlist")
                    btn_export = gr.Button("Export handoff", variant="primary")
                short_out = gr.Markdown(value=shortlist_show())

                btn_hunt.click(skill_hunt, inputs=[hunt_q, hunt_limit], outputs=hunt_out)
                hunt_q.submit(skill_hunt, inputs=[hunt_q, hunt_limit], outputs=hunt_out)
                btn_trend.click(skill_trending, inputs=[hunt_limit], outputs=hunt_out)
                btn_inspect.click(skill_inspect, inputs=skill_ref, outputs=hunt_out)
                skill_ref.submit(skill_inspect, inputs=skill_ref, outputs=hunt_out)
                btn_add.click(shortlist_add, inputs=[skill_ref, skill_note], outputs=short_out)
                btn_rm.click(shortlist_remove, inputs=skill_ref, outputs=short_out)
                btn_list.click(shortlist_show, outputs=short_out)
                btn_export.click(skill_export_handoff, outputs=hunt_out)

        gr.Markdown(
            '<p class="panel-note">v2.4 · Dynamic Ollama Discovery + Quick Presets + Session Outbox Export · Ops MCP + Skill Hunter.</p>'
        )

    return demo


if __name__ == "__main__":
    theme = gr.themes.Soft(
        primary_hue="emerald",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("IBM Plex Sans"),
    ).set(
        body_background_fill="#0b0f14",
        block_background_fill="#121821",
        border_color_primary="#1e2a3a",
    )
    app = build()
    app.queue().launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        theme=theme,
        css=CSS,
    )
