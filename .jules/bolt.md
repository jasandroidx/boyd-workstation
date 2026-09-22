## 2026-03-22 - SSLContext Creation Overhead in urllib Requests
**Learning:** Calling `ssl.create_default_context()` on every HTTP request creates and parses system default certificates each time, taking ~40ms per call. Memoizing the `SSLContext` instance across requests reduces this per-request overhead to <0.001ms.
**Action:** Always memoize or reuse `ssl.SSLContext` instances (e.g. via `@functools.lru_cache(maxsize=1)`) when making repeated HTTPS calls with `urllib.request`.
