# Local workspace interface

Version 0.6.0.dev0 presents the scientific workflow in a responsive research workspace. The navigation connects Analysis and claims, Controls, Evidence library, Execution, Scientific audit, and Evaluation. Open and Export keep file actions together; Save review bundle remains available in the header. The interface uses the existing local server and needs no frontend build step.

## Visual structure

A navy navigation rail provides a stable frame. The light canvas uses white surfaces, thin borders, restrained shadows, and teal actions. Serif headings distinguish the scientific question from form labels and record details. System fonts and local SVG icons keep the application self-contained. The small claim/control/source/result motif illustrates the review framework; it contains no measured data or performance claim.

| Role | Color token |
| --- | --- |
| Navigation | `#172b3a` |
| Primary text | `#182d3d` |
| Canvas | `#f5f7f8` |
| Surfaces | `#ffffff` |
| Primary action | `#217c73` |
| Secondary text | `#627480` |

Four summary cards count claims, reviewed controls plus candidates, publication records, and results with COMPLETED execution status. Zero remains zero. A publication count does not imply statement support. A completed execution does not imply a passed control or a valid scientific claim. Control numbers such as C01 reflect collection order, not scientific ranking.

Cards retain exact evidence-state labels, scientific rationale, expected behavior, failure interpretation, and limitations. Assumptions and provenance expand separately. Positive and negative class accents identify class; state labels identify evidence status. Color is supplemental. METHOD_BASED has a neutral label, incomplete evidence uses amber, conflicting evidence uses red, and EVIDENCE_BACKED uses green. State colors do not authenticate imported review receipts.

Search matches a control's name, rationale, expected behavior, identifier, or linked claim statement. The class filter uses the existing control ontology; a claim filter appears for multiple claims. Filters combine without editing records, changing priorities, or promoting evidence status. Control details display the full claim, while result panels name the executed control and challenged claim. Audit panels display the assessed claim. Result details retain IDs, assumptions, recorded parameters, seed, software versions, runner hash, and any prespecified rule.

Execution fields follow the selected procedure. References ask for the expected effect and absolute tolerance; resampling asks for draws and seed, with coverage for bootstrap intervals. An explicit CSV inspection shows dimensions and an original-byte hash in a restrained summary surface. Shape checking does not run a control or establish sampling assumptions. A separate JSON export retains only that summary.

Scientific reports use the same restrained colors and serif title, actual record summaries, internal links, mobile layouts, and print styles. Control and claim references resolve within the report. Empty sections remain explicit. No script, remote font, or external image is required.

## Navigation and accessibility

The selected section has explicit tab and panel relationships. Arrow keys, Home, and End move selection; only the selected navigation tab participates in normal Tab traversal. A skip link reaches the main workspace. The mobile drawer confines keyboard focus while the canvas is inert, closes with its close button, Escape, or the backdrop, and returns focus appropriately. File menus also close with Escape. Busy operations and errors announce their actual states.

Forms retain native labels, required fields, and unselected scientific categories. Review and judgment headings scroll below the fixed header. Metric tables become labeled rows on narrow screens. The interface respects reduced-motion preferences and retains visible keyboard focus.

[Browser checks](../scripts/check_ui.cjs) cover all six sections at 375, 768, 1024, and 1440 pixels, combined claim/class filters, record bindings, keyboard tabs, mobile focus boundaries, reduced motion, text-only rendering, input inspection, draft protection, replacement, and responsive reports. [The recorded observations](validation/ui_checks.json) include scope and timestamps. Screenshots were visually inspected. These checks do not establish full accessibility conformance, screen-reader compatibility, print pagination, or usability across all browsers. Independent researcher usability review remains pending.

## Local operation

No external images, fonts, UI libraries, analytics, or storage were added. Projects and form signatures remain in browser memory. Export needed tracks recorded revisions; Unrecorded inputs identifies edited form values, and reverting a form clears that state. Bundle prepared means a complete download was prepared, not verified on disk. Retain it before closing. The status also appears in the overview at narrow widths.

Opening another project or starting an empty workspace asks before replacement. Candidate and source-review switching, example/draft application, and evaluation replacement protect unrecorded form edits. Judgment tracking includes all cases; changing the visible case alone is not a new judgment. Accepted project replacement resets prior forms, reviews, evaluations, input selection, credentials, previews, and the ledger. Public literature and hosted reasoning requests still require exact-payload approval. See [USAGE.md](USAGE.md), [PRIVACY.md](../PRIVACY.md), and [SECURITY.md](../SECURITY.md).
