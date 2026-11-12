# ADR 0006: Static browser workspace

Status: Accepted for the local research alpha, 2026-11-12.

## Context

The Render service that hosted the prototype is suspended for the remainder of the month after the shared free allowance ran out. Hugging Face now requires a paid plan for Docker Spaces. The owner chose a free static deployment on GitHub Pages, which serves files and cannot run the Python service. The scientific core needs only Pydantic and the standard library, and Pyodide 314.0.7 provides CPython 3.14.2 with Pydantic 2.12.5 compiled for WebAssembly.

## Decision

Run the unchanged interface and scientific dispatch in the visitor's browser. `web/browser.js` answers the interface's `/api/` requests in the page and sends each action to a dedicated module worker. `web/browser_worker.js` downloads Pyodide's core files, the package wheels, and the Controlomics wheel from the same site, checks each against the SHA-256 in `browser_manifest.json`, retries an interrupted download, and only then starts Pyodide, because Pyodide waits indefinitely when its WebAssembly download is refused. The remaining start-up is bounded at 120 seconds, and the page retries a failed start twice before reporting it. The worker then calls `controlomics.browser.dispatch`. That function calls the same `handle_action` as the local server and returns the local server's status codes and fixed redacted messages. The interface accepts the `BROWSER` mode only when the page runtime has registered itself, and only over HTTPS or on a loopback host. It otherwise uses the local-mode wording, which remains accurate: records stay in this browser on this computer.

`scripts/build_browser.py` builds the site from a wheel and pinned Pyodide files. It accepts the five core files only when their SHA-256 matches values checked against the integrity-verified npm release, and package wheels only when they match that lock file. The published site loads nothing from a third party. Pyodide's JSPI path is hidden in the worker because Controlomics never suspends WebAssembly and that path made start-up more than twenty times slower in Chrome 157.

Fixed-template execution cannot start a process in the browser. `InProcessRunner` replaces `subprocess` for `execute_local` only, runs the hash-checked `run_control.py` as `__main__` in the worker's interpreter with the same arguments, and removes the modules it imported from its package folder. The page enforces the local time limit by ending the worker after 37 seconds, 35 for the runner and two for package preparation, then returns the fixed timeout reply and starts a new worker. `execution.py` and the frozen numerical sources are unchanged.

Literature and model requests keep the existing preparation, screening, exact-approval, allowlist, and ledger code. `SafeTransport.open_event` now holds the shared approval, allowlist, and NOT_STARTED ledger step. `BrowserTransport` performs it and then asks the page to send the exact approved request, recording nothing until the outcome returns. The page sends it with HTTPS only, `redirect: "error"`, omitted credentials and referrer, no caching, a 20-second timeout, and a streamed 2 MiB response bound, then repeats the action with the outcome keyed by request hash. Preparation is deterministic, so the repeated action reproduces the same hash. The ledger records the phase the page reached. A visitor's model key stays in the page and is added only to that request's authorization header.

`.github/workflows/pages.yml` builds the site from `main` and publishes it. Only its deploy job holds `pages: write` and `id-token: write`.

## Alternatives and consequences

A paid host, a different free container host, or waiting for Render would keep the server boundary. GitHub Pages keeps every component free and leaves research inputs in the browser, but several guarantees change. The browser resolves names and negotiates TLS, so the transmission-time public-address check and the explicit TLS floor no longer apply; the browser's own certificate checks do. A refused redirect cannot be distinguished from a network failure, so both are recorded as ATTEMPTED. The page cannot set a User-Agent. Providers that refuse cross-origin requests fail after an attempt. GitHub Pages cannot send headers, so the content policy is a meta element without `frame-ancestors`, and framing is not prevented. The worker is served without a policy of its own. Execution shares the worker's interpreter rather than running in a separate operating-system process. The first visit downloads about 15.7 MB.

The local server, hosted adapter, Render Blueprint, scientific procedures, and evidence gates are unchanged. The browser workspace does not establish scientific suitability, independent security review, screen-reader behavior, or availability.
