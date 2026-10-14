# Hosting and distribution

Controlomics supports a local workspace and a full hosted prototype. Source distribution and research processing have separate boundaries.

The hosted prototype is available at [controlomics.onrender.com](https://controlomics.onrender.com/). The [scoped deployment record](validation/live_render_v0.6.12.json) describes the performed synthetic checks and their limits.

| Component | Location | Purpose |
| --- | --- | --- |
| Source repository | GitHub | Inspect code, report software issues, and contribute changes |
| Release downloads | GitHub Releases | Obtain versioned packages with recorded hashes |
| Local workspace | Researcher's computer | Process inputs on that computer through the loopback service |
| Hosted prototype | Render Python web service | Temporarily process explicitly consented research inputs |
| Optional literature or model provider | Separately approved external service | Receive only screened selected public fields after exact-request approval |

## Full hosted prototype

`render.yaml` defines a free Python web service in Singapore, using `.python-version` and exact dependencies in `requirements-cloud.lock`. Its build installs the package, and Gunicorn loads `controlomics.hosted:create_app()` with `gunicorn.conf.py`. Automatic deployment waits for linked branch checks to pass. `/healthz` is the health endpoint. There is no database, persistent disk, saved upload, model weight, or container requirement. This configuration file describes a deployment; it does not itself establish that a live service exists.

The six-section workspace uses the same scientific actions as the local application, including description drafting, control specifications and reviews, numeric inspection and execution, reports and packages, review archives, and evaluation. Optional model and literature requests retain their separate approval boundary and provider terms. External models are not included in the hosting price.

On first use, the interface identifies temporary cloud processing and asks for consent. A signed per-browser session, a bound request token, and that consent are checked before reading a scientific action body. Inputs pass over HTTPS to the configured service. Project snapshots, source-review text, numeric inputs, and evaluation records are processed in request memory or owned temporary directories as required. The application saves no project database or uploads. Export work before closing; browser memory is the workspace, and a prepared download is not proof that it was retained.

Hosted project exports and packages carry historical processing attestations. Those records are not authenticated evidence of processing and cannot authorize a new session. They explain the exception to the unchanged local baseline privacy flags. Raw inputs remain excluded from dispatched packages and review archives. Application logs omit input and credential values; the hosting provider can collect connection and operational metadata. Ordinary cleanup is attempted, with crash and erasure limits described in [PRIVACY.md](../PRIVACY.md).

## Service configuration

The hosted adapter requires `CONTROLOMICS_SESSION_SECRET`, at least 32 bytes of secret material. The Blueprint asks Render to generate a random 256-bit value; keep it out of source files and scientific exports. `CONTROLOMICS_TRUST_PROXY=render` permits HTTPS forwarding only from a direct private or loopback peer, with exact Host and forwarding checks. `PUBLIC_ORIGIN` may explicitly set the canonical HTTPS origin; otherwise the adapter uses Render's `RENDER_EXTERNAL_URL`. It never derives authority from forwarded host or client-IP headers.

Gunicorn runs one worker with four threads, HTTP/1 only, a 10-second socket read-inactivity limit, and a 30-second total header/body read deadline. Response writes have a separate 10-second bound so the read deadline does not limit a completed 35-second numeric calculation. The metadata-only worker heartbeat uses Linux `/dev/shm`; it contains no research inputs. Application admission and numeric budgets are documented in [SECURITY.md](../SECURITY.md). Scaling to several workers, instances, public proxies, custom origins, or stored projects requires a separately assessed configuration; the bounded in-memory session and action limits are per worker. The loopback `controlomics serve` command remains local and must not be exposed publicly.

Render's free service can sleep after inactivity, restart, and pause at its shared usage limits. Its Blueprint rejects a custom `maxShutdownDelaySeconds`, so the configuration uses Render's default shutdown deadline. That deadline can terminate an in-flight action before the application's execution or graceful-shutdown timeout. A cold start invalidates sessions and requires renewed consent; the browser retains work and never automatically repeats a request. Free compute can be slower than a scientific workstation, and valid numeric work can exceed the fixed execution timeout. There is no uptime or result guarantee. Plan availability and limits can change; consult [Render's free-service documentation](https://render.com/docs/free).

[Render's service documentation](https://render.com/docs/web-services), [Blueprint reference](https://render.com/docs/blueprint-spec), [environment variables](https://render.com/docs/environment-variables), and [privacy policy](https://render.com/privacy) describe the host. Third-party hosting must never be described as collecting no information.

GitHub Pages serves static files and cannot run this Python service. Its availability does not provide a working Controlomics workspace; see [GitHub's Pages description](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages).
