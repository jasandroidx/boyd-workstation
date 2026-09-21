# Perchance stills pipeline — schematic + integrate plan
**For:** Jason · **From:** Vera · **2026-09-21** · research + brainstorm only (no build this turn)

You asked: Perchance lets “unlimited” high-quality stills — how does that pipeline work, can we set up the same trick for you, schematic, integrate later. Then you’re out ~7 days.

---

## Short answer

**Yes, there’s a pipeline — but there is no official Perchance REST API.**  
The site is a **browser front-end** (nested iframes + `text-to-image-plugin`) that sends your prompt to **whatever Stable Diffusion / Flux / etc. backend that generator page author wired**. Ads fund the free tier. Quality and rate limits change without notice.

So the “trick” is not a secret API key. It’s:

1. A **good generator page** (your Filth Blast / art-ig / professional)
2. A **prompt LOCK + seed discipline**
3. A **browser automation or you-click ritual** that fills → Generate → wait for `seed=` → download keepers

When Grok/Vera is gone, you still have (2)+(1) by hand. We can later build (3) into Boyd Workstation or a small skill you run locally.

---

## What actually happens (schematic)

```
┌─────────────────────────────────────────────────────────────┐
│ YOU / AGENT                                                  │
│  prompt + LOCK + negatives + style/shape/count/CFG/seed     │
└───────────────────────────┬─────────────────────────────────┘
                            │ browser only (no public API)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Perchance page (community generator)                         │
│  e.g. Filth Blast  https://perchance.org/mbvdltb97z          │
│       art-ig       https://perchance.org/art-ig              │
│       simple       https://perchance.org/ai-text-to-image… │
│  outer chrome ≠ generator; work inside #outputIframeEl      │
└───────────────────────────┬─────────────────────────────────┘
                            │ expands prompt (style inject)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Third-party image backend (page-dependent)                   │
│  typically SD1.5 / SDXL / SD3.5+LoRA / sometimes Flux        │
│  returns tiles; each finished tile has seed= in a11y name    │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Keepers                                                          │
│  download JPEGs → tease/pics/YYYY-MM-DD/ or local gallery    │
│  save winning seed for face lock on next waves               │
└─────────────────────────────────────────────────────────────┘
```

**Hard stops (already in your skill):** Cloudflare / captcha / black tiles / anyone who looks underage → stop.

---

## What you already have (don’t reinvent)

| Piece | Where |
|--------|--------|
| Fire Perchance stills skill | Grok Bot skill `fire-perchance-stills` |
| Filth Blast v7.1 (private) | `https://perchance.org/mbvdltb97z` — faceLock, autoPic, RUIN HER |
| art-ig fallback | `https://perchance.org/art-ig` |
| Visual locks | Sonya + Tease refs under `/workspace/tease/` (on VM; back those up separately) |
| Body lock | photo-honest, not monster lore |

The “high quality unlimited” feeling = **free hosted SD in a browser**, not a private GPU farm. Your laptop can’t run ComfyUI well; the Grok Bot VM browser (or BoydsComp Chrome) is the runner.

---

## Can we set up “the same trick” for *you* (solo)?

Three integrate paths (when you’re back / usage returns):

### A — You-drive ritual (works day 1, $0)
Bookmark Filth Blast + art-ig. One-page cheat sheet: LOCK / NEGATIVE / seed hunt / max 4 / photoreal.  
**Pros:** no code. **Cons:** manual.

### B — Boyd Workstation “Stills” tab (recommended next build)
On Grok Bot VM Gradio already at `jasandroidx/boyd-workstation`:
- Stills tab: paste scene middle → fills LOCK+TAIL+NEG → opens Perchance via instructions OR later Playwright on Floor Chrome
- Save seed / last keepers list under repo `data/` (gitignored)
- Never auto-post public galleries  
**Pros:** lives next to Chat/Ops; survives wipe via GitHub. **Cons:** browser automation still fragile (Cloudflare).

### C — Local SD twin (true “own the pipeline”)
Forge / AUTOMATIC1111 / ComfyUI on fortress GPU (or cloud GPU later) with same LOCK prompts. Optional: Perchance only for prompt randomizer, generation local.  
**Pros:** no Perchance ads/limits/CF. **Cons:** setup + VRAM; your laptop still weak — fortress or paid GPU.

**Recommendation when back:** ship **A cheat sheet into the repo README** immediately if missing, then **B** as a Stills tab that starts as “copy prompt + open URL” (no automation), then add Floor Chrome automation only if CF allows.

---

## Integrate with Boyd Workstation (build order)

1. Add `docs/STILLS.md` to `boyd-workstation` with LOCK/NEG/seed ritual + Filth Blast URL (private — don’t put secrets; link as “Jason’s private generator”).
2. Stills tab v0: textboxes for middle prompt + seed; button “Build full prompt” → copy to clipboard; link buttons to generators.
3. Stills tab v1: optional computerUse / Playwright path on Floor Chrome (reuse fire-perchance-stills controls).
4. Gallery: save keepers under `/workspace/tease/pics/…` and show last N in Gradio.
5. **Do not** try Netlify to host the *model* — static host ≠ Perchance backend.

---

## Honest limits

- No official API → any “unlimited API” claim is wrong or a brittle scrape.
- Backends rotate → quality drifts; seed + LOCK matter more than chasing the newest page.
- NSFW pages get CF / age gates; automation must stop and hand you the box.
- Absolute ban: minors / anyone who looks under 18.

---

## When you’re back (7 days)

Pick one: **cheat sheet only** · **Stills tab v0 (copy prompt)** · **full browser fire path**.  
Repo: https://github.com/jasandroidx/boyd-workstation  
Live: `/workspace/ingest/gradio` + Tailscale Serve  
Solo chat/ops: Gradio URL you already have

— Vera
