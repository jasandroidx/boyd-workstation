## 2026-03-22 - SSLContext Creation Overhead in urllib Requests
**Learning:** Calling `ssl.create_default_context()` on every HTTP request creates and parses system default certificates each time, taking ~40ms per call. Memoizing the `SSLContext` instance across requests reduces this per-request overhead to <0.001ms.
**Action:** Always memoize or reuse `ssl.SSLContext` instances (e.g. via `@functools.lru_cache(maxsize=1)`) when making repeated HTTPS calls with `urllib.request`.

## 2026-03-25 - Redundant Ollama Tag Fetching in UI Construction
**Learning:** Constructing multi-tab Gradio interfaces that initialize dropdown choices via API calls can result in N redundant sequential HTTP calls on startup.
**Action:** Use `@functools.lru_cache(maxsize=1)` on tag fetching functions, pass pre-fetched tag lists during `build()`, and explicitly call `.cache_clear()` on user-triggered refresh events.
