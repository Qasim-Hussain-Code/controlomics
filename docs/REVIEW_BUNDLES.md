# Local review bundles

Save review bundle in the workspace exports a ZIP containing fixed known members: `manifest.json`, `project.json`, `network_audit.json`, and `report.html`. If an evaluation is loaded, `evaluation.json` and `annotation_revisions.json` are included. Only recorded annotation snapshots are exported; save your judgments first. Raw CSV files, full supplied source texts, and authorization credentials are excluded. Project descriptions and selected public query text can still contain private research information. Review exports before sharing.

The manifest records the software version, creation time, project identifier, artifact sizes and SHA-256 hashes, and limitations. These hashes detect changes relative to the supplied manifest. They do not authenticate a replaced manifest, reviewer identity, actual execution, or ledger completeness. Model request bodies are absent, so their complete request hashes cannot be reconstructed from the saved ledger alone.

Open review bundle validates the entire archive before restoring records into browser memory. Imports reject unsupported names, duplicate members, traversal names, symbolic links, encryption, unsupported compression, missing members, changed hashes, invalid records, and inconsistent revision chains. Nothing is extracted from user-controlled archive paths. Imported HTML is never displayed or executed; report export regenerates escaped HTML from validated records.

Archive size is limited to 1 MiB, expanded contents to 8 MiB, and each member to 4 MiB. Project, evaluation, and other parsed JSON records retain the 2 MiB parsing budget. The ledger and annotation revision sidecar each accept at most 500 events. Large workspaces need separately retained local snapshots rather than bypassing these limits.

The network ledger accepts only known metadata fields, screened SAFE public text, a destination, request/body hashes, timing, transmission state, optional response receipt, and credential presence. It rejects raw bodies, authorization headers, unexpected fields, and inconsistent completed receipts. An empty ledger means no supplied events; it is not independently verified absence of network activity.

```powershell
.\.venv\Scripts\controlomics.exe bundle-export local_projects/project.json --network-audit local_projects/network_audit.json --output local_projects/review.zip
.\.venv\Scripts\controlomics.exe bundle-import local_projects/review.zip --directory local_projects/restored
```

Use optional `--evaluation` and `--revisions` on export to include those records. Import requires an absent destination, including rejection of existing empty directories. It prepares only fixed filenames after validation, regenerates the report, and then exposes the complete directory. Ordinary preparation failures attempt staging cleanup; crashes or denied cleanup can leave files beside the destination. Revisions retain hashes rather than previous snapshot content; preserve earlier exported snapshots to inspect prior judgments and evidence.
