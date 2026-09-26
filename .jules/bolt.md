## 2026-03-22 - SSLContext Creation Overhead in urllib Requests
**Learning:** Calling `ssl.create_default_context()` on every HTTP request creates and parses system default certificates each time, taking ~40ms per call. Memoizing the `SSLContext` instance across requests reduces this per-request overhead to <0.001ms.
**Action:** Always memoize or reuse `ssl.SSLContext` instances (e.g. via `@functools.lru_cache(maxsize=1)`) when making repeated HTTPS calls with `urllib.request`.

## 2026-03-22 - Redundant Network Calls in Multi-Tab Gradio UI Construction
**Learning:** Instantiating multiple dropdowns in a multi-tab Gradio UI where each dropdown fetches remote model tags independently causes redundant network requests during `build()`. Fetching tags once during build and reusing the initial tags across dropdown choices eliminates redundant calls and prevents multi-fold timeout delays when the service is slow.
**Action:** Always pass pre-fetched initial choices into multi-component UI builders, and set `ThreadPoolExecutor(max_workers=len(tasks))` for fixed I/O-bound fan-out operations.
