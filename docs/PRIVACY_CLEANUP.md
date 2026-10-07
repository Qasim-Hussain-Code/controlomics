# Personal-information cleanup

The 2026-10-07 cleanup concerns private project ownership and local user-identifying artifacts in this workspace. It does not alter operating-system accounts, files elsewhere on the computer, conversation history, or public bibliographic authorship and third-party license notices.

Personal attribution is removed from current instructions, README, package configuration, interface/report footers, citation metadata, and package-check code. The incomplete personal citation record is replaced by [a software-identification note](CITATION.md). Existing local demonstration reports are minimized, older generated wheels are removed, and current package metadata and screenshots are regenerated without that attribution.

Historical package observations explicitly mark removal of the personal author field; their numerical/software observations and original artifact hashes are retained. The owner also authorized local Git-history sanitization. Its eight-commit sequence, parent graph, dates, and current tree were preserved with project-only attribution and empty emails. Thirty-one historical text blobs were minimized, the personal citation file was omitted from seven historical snapshots, and thirty-two occurrences of superseded screenshots were omitted. Current attribution-free screenshots remain available.

Old Git objects and reflogs were pruned. [The history check](validation/git_history_cleanup_checks.json) inspected all 423 remaining objects and non-object Git files and found no matching former private identities. [The current-file check](validation/privacy_cleanup_checks.json) separately covers working files and local artifacts. Commit IDs changed. This is ordinary logical removal from the local repository, not a claim of forensic disk erasure or control of external backups.

Reviewer forms recommend identifiers rather than personal names. Existing schema fields remain compatible; an identifier does not authenticate a person or prove expertise. Human scientific review still requires truthful provenance. A study that needs a real-identity mapping should keep it in separately protected private records and control its disclosure.

Research records can contain identifying text in descriptions, excerpts, source metadata, locators, queries, and annotations. Pattern scans cannot guarantee recognition of every personal detail. Raw research files remain local, and this cleanup does not authorize uploading, publishing, or recruiting reviewers. The application's virtual environments and launchers can retain local installation paths required for execution; they are excluded from distributable source and wheel artifacts.

Cleanup observations and verification are recorded separately from numerical validation. The frozen numerical source files and their protocol hashes must remain unchanged by attribution removal. Re-rendered screenshots are current privacy-phase captures, not untouched historical image artifacts.
