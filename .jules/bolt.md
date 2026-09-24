## 2026-03-22 - SSLContext Creation Overhead in urllib Requests
**Learning:** Calling `ssl.create_default_context()` on every HTTP request creates and parses system default certificates each time, taking ~40ms per call. Memoizing the `SSLContext` instance across requests reduces this per-request overhead to <0.001ms.
**Action:** Always memoize or reuse `ssl.SSLContext` instances (e.g. via `@functools.lru_cache(maxsize=1)`) when making repeated HTTPS calls with `urllib.request`.

## 2026-09-24 - Redundant Local Ollama Tag Requests during UI Build
**Learning:** Initializing multiple Gradio dropdowns in separate tabs without passing shared `dynamic_models` caused `fetch_ollama_tags()` to trigger 4 identical synchronous HTTP requests (~45ms each or up to 5s on timeout) during UI construction. Adding a 10s TTL cache and passing pre-fetched tags during `build()` reduced redundant network calls to 0 ms on subsequent tab creations.
**Action:** Always pre-fetch shared dynamic options once during UI construction and use TTL caching with an explicit `force_refresh` parameter for manual refresh triggers.
