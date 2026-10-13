# Hosting and distribution

Controlomics separates public software distribution from private research execution.

| Component | Location | Purpose |
| --- | --- | --- |
| Source repository | GitHub | Inspect code, report software issues, and contribute reviewed changes |
| Release downloads | GitHub Releases | Obtain a versioned wheel or source package with recorded hashes |
| Project documentation | Repository documentation; optionally GitHub Pages | Read methods, architecture, installation, validation, and limitations |
| Scientific workspace | Researcher's computer | Process project snapshots and selected numeric inputs locally |
| Optional literature or model service | Explicitly approved external provider | Receive only screened selected public fields after exact-request approval |

The installed application binds to `127.0.0.1`; the browser connects to the local Python service. Raw research inputs stay in that environment. There is no hosted project database or automatic synchronization.

GitHub Pages serves static HTML, CSS, JavaScript, and generated documentation. It cannot run this Python service. Publishing the interface assets alone does not provide a functioning hosted Controlomics application.

A public multiuser application would require a separately designed and assessed deployment: per-user authentication and authorization, isolated projects and execution, credential handling, resource controls, and an explicit data-processing policy. The local preview is not qualified for that deployment. A public tunnel or reverse proxy does not establish those boundaries.

Project pages and repository services have their own hosting privacy policies. GitHub Pages records visitor IP addresses for security; that is distinct from the local application's lack of telemetry. Never describe third-party hosting as collecting no information.

The [GitHub Pages description](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages), [Pages setup documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site), and [release documentation](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository) describe these services. Their availability does not imply that a site or release has been published.
