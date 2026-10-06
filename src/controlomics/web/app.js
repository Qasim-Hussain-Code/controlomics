"use strict";
const state = {project: null, audit: [], token: null, pending: null, busy: false};
const $ = id => document.getElementById(id);
const lines = text => text.split(/\r?\n/).map(value => value.trim()).filter(Boolean);
function message(text, error = false) { $("status").textContent = text; $("status").className = error ? "status error" : "status"; }
async function action(work) { if (state.busy) return; state.busy = true; message("Processing the requested operation..."); try { await work(); } catch (error) { message(error.message || "Operation failed.", true); } finally { state.busy = false; } }
async function api(path, body, binary = false) {
  if (!state.token) throw new Error("Local session is not ready. Reload the page.");
  const response = await fetch(path, {method: "POST", headers: {"Content-Type": "application/json", "X-Controlomics-Token": state.token}, body: JSON.stringify(body)});
  if (binary && response.ok) return response.blob();
  const data = await response.json();
  if (data.network_audit) state.audit.push(...data.network_audit);
  if (!response.ok || data.error) { render(); throw new Error(data.error || "Operation failed."); }
  return data;
}
function requireProject() { if (!state.project) throw new Error("Create or open a project first."); return state.project; }
function switchView(name) { document.querySelectorAll(".view").forEach(view => { view.hidden = view.id !== "view-" + name; }); document.querySelectorAll(".tab").forEach(tab => { const selected = tab.dataset.view === name; tab.classList.toggle("active", selected); tab.setAttribute("aria-selected", String(selected)); }); }
function node(tag, text, className) { const element = document.createElement(tag); if (text !== undefined) element.textContent = text; if (className) element.className = className; return element; }
function field(label, value) { const wrapper = node("div", undefined, "field"); wrapper.append(node("strong", label), node("p", value || "Not supplied")); return wrapper; }
function empty(text) { return node("p", text, "empty"); }
function download(content, filename, type = "application/json") { const blob = content instanceof Blob ? content : new Blob([content], {type}); const url = URL.createObjectURL(blob); const anchor = node("a"); anchor.href = url; anchor.download = filename; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
function accept(data, notice) { if (data.project) state.project = data.project; render(); message(notice); }
function render() {
  const project = state.project;
  $("export-project").disabled = $("export-report").disabled = !project;
  for (const id of ["control-list", "evidence-list", "result-list", "audit-list", "execution-control"]) $(id).replaceChildren();
  if (!project) { for (const id of ["control-list", "evidence-list", "result-list", "audit-list"]) $(id).append(empty("Create or open a local project to inspect this section.")); return; }
  const controls = [...project.controls, ...project.candidates];
  for (const control of controls) {
    const card = node("article", undefined, "control-card"); const top = node("div", undefined, "card-top");
    top.append(node("span", control.control_class, "badge" + (control.control_class === "NEGATIVE" ? " negative" : "")), node("span", control.evidence_status, "evidence-state"));
    card.append(top, node("h3", control.control_name), field("Scientific rationale", control.scientific_rationale), field("Expected behavior", control.expected_behavior), field("Failure interpretation", control.failure_interpretation), field("Limitations", control.limitations.join(" ")));
    const details = node("details"); details.append(node("summary", "Inspect assumptions and provenance"), field("Method basis", control.method_basis), field("Uncertainties", control.uncertainties.join(" ")), field("Claim tested", control.claim_tested), field("Context compatibility", control.context_compatibility.status), field("Priority", control.priority + ": " + control.priority_rationale));
    card.append(details, node("div", control.scientific_level + " / " + control.execution_status, "card-foot")); $("control-list").append(card);
  }
  if (!controls.length) $("control-list").append(empty("No appropriate control was specified. Review the analysis context and recorded abstentions."));
  for (const control of project.controls.filter(item => ["METHOD_BASED", "EVIDENCE_BACKED"].includes(item.evidence_status) && !project.execution_plans.some(plan => plan.control_id === item.control_id))) {
    const option = node("option", control.control_class + ": " + control.control_name); option.value = control.control_id; $("execution-control").append(option);
  }
  for (const evidence of project.evidence) {
    const article = node("article", undefined, "panel publication"); article.append(node("h3", evidence.title || "Title unavailable"), node("p", evidence.authors.join("; ") + (evidence.year ? "; " + evidence.year : "")));
    const links = node("div", undefined, "actions");
    for (const identifier of evidence.identifiers) {
      const link = node("a", identifier.namespace + ": " + identifier.value); link.rel = "noopener noreferrer"; link.target = "_blank";
      if (identifier.namespace === "DOI") link.href = "https://doi.org/" + encodeURIComponent(identifier.value);
      else if (identifier.namespace === "PMID") link.href = "https://pubmed.ncbi.nlm.nih.gov/" + encodeURIComponent(identifier.value) + "/";
      else if (identifier.namespace === "PMCID") link.href = "https://pmc.ncbi.nlm.nih.gov/articles/" + encodeURIComponent(identifier.value) + "/";
      else continue;
      links.append(link);
    }
    article.append(links, field("Identity and source", evidence.existence_status + " / " + evidence.source), field("Scientific limitation", evidence.limitations.join(" "))); $("evidence-list").append(article);
  }
  if (!project.evidence.length) $("evidence-list").append(empty("No literature has been retrieved for this project. A plausible recommendation is not external evidence."));
  for (const result of project.results) {
    const article = node("article", undefined, "panel"); article.append(node("h3", "Recorded control result"), field("Status", result.execution_status + " / " + (result.outcome || "No binary interpretation")), field("Interpretation", result.interpretation));
    if (result.effect_estimate) article.append(field(result.effect_estimate.name, String(result.effect_estimate.value)));
    if (result.p_value !== null) article.append(field("Permutation p value", String(result.p_value)));
    if (result.confidence_interval) article.append(field("Confidence interval", result.confidence_interval.lower + " to " + result.confidence_interval.upper + " (coverage " + result.confidence_interval.coverage + ")"));
    article.append(field("Warnings", result.warnings.join(" ")), field("Input hashes", result.input_hashes.map(item => item.input_id + ": " + item.sha256).join("; "))); $("result-list").append(article);
  }
  if (!project.results.length) $("result-list").append(empty("No control has been executed. Download a reproducible package or run a specified numeric control locally."));
  for (const audit of project.audits) {
    const article = node("article", undefined, "panel"); article.append(node("p", audit.assessment.replaceAll("_", " "), "notice"), field("Assessment rationale", audit.rationale));
    for (const finding of audit.uncertainties) article.append(node("div", finding, "finding"));
    article.append(field("Limitations", audit.limitations.join(" "))); $("audit-list").append(article);
  }
  $("ledger").textContent = JSON.stringify({provenance: project.provenance, network_audit: state.audit}, null, 2);
}
document.querySelectorAll(".tab").forEach(tab => tab.addEventListener("click", () => switchView(tab.dataset.view)));
$("analysis-form").addEventListener("submit", event => { event.preventDefault(); action(async () => {
  const form = new FormData(event.target); const value = name => String(form.get(name) || "").trim();
  const context = {}; for (const key of ["organism", "tissue", "data_modality"]) if (value(key)) context[key] = value(key);
  const intake = {question: value("question"), analysis_description: value("analysis_description"), methods: lines(value("methods")), observed_result: value("observed_result"), claim: value("claim"), claim_category: value("claim_category"), computational_support: value("computational_support"), biological_context: context, design: {sampling_unit: value("sampling_unit") || null, data_partition: value("data_partition") || null}, assumptions: lines(value("assumptions"))};
  const data = await api("/api/analyze", {intake}); state.audit = []; accept(data, "Local method controls specified. Biological support and applicability remain unvalidated."); switchView("controls");
}); });
function example(kind) {
  const common = {organism: "Saccharomyces cerevisiae", tissue: "", assumptions: "This is a hypothetical development example, not observed biology.", sampling_unit: "Independent culture", data_partition: "Each culture is an independent unit."};
  const values = kind === "rna" ? {...common, question: "Does a hypothetical treatment change transcript abundance?", claim: "Transcript abundance differs between hypothetical conditions.", analysis_description: "A between-culture differential abundance comparison. The primary analysis was conducted separately.", methods: "Count-based differential abundance comparison", observed_result: "Hypothetical reported abundance differences; no measurements supplied.", claim_category: "COMPARATIVE", computational_support: "COMPARATIVE", data_modality: "bulk transcript counts"} : {...common, organism: "", question: "Can image features distinguish hypothetical cell morphology labels?", claim: "An image-feature classifier predicts morphology labels in new cultures.", analysis_description: "A supervised image-feature classifier evaluated on held-out cultures.", methods: "Image-feature classification", observed_result: "Hypothetical discrimination; no measured score supplied.", claim_category: "PREDICTIVE", computational_support: "PREDICTIVE", data_modality: "microscopy image features", data_partition: "All images from a culture remain in the same data partition."};
  for (const [name, value] of Object.entries(values)) $("analysis-form").elements.namedItem(name).value = value;
  switchView("analysis"); message("Loaded a hypothetical example. Review the fields, then create the control audit.");
}
$("example-rna").addEventListener("click", () => example("rna")); $("example-ml").addEventListener("click", () => example("ml"));
async function fileJSON(input) { const file = input.files[0]; if (!file) return null; if (file.size > 2 * 1024 * 1024) throw new Error("Local JSON exceeds the 2 MiB limit."); return JSON.parse(await file.text()); }
$("project-file").addEventListener("change", () => action(async () => { const project = await fileJSON($("project-file")); if (!project) return; state.audit = []; accept(await api("/api/analyze", {project}), "Opened and audited a local project. Review its evidence receipts before relying on them."); switchView("controls"); $("project-file").value = ""; }));
$("export-project").addEventListener("click", () => { if (state.project) download(JSON.stringify(state.project, null, 2), "project.controlomics.json"); });
$("export-audit").addEventListener("click", () => download(JSON.stringify(state.audit, null, 2), "network_audit.json"));
$("export-report").addEventListener("click", () => action(async () => { const report = await api("/api/report", {project: requireProject(), network_audit: state.audit}, true); download(report, "controlomics.report.html"); message("Downloaded the local report. Review it before sharing."); }));
async function preview(kind, settings) { requireProject(); const result = await api("/api/" + kind + "/preview", settings); state.pending = {kind, settings, hash: result.approve_hash}; $("request-preview").textContent = JSON.stringify(result, null, 2); $("request-dialog").showModal(); message("No external request has been sent. Review the displayed payload."); }
$("literature-form").addEventListener("submit", event => { event.preventDefault(); action(() => preview("literature", {provider: $("literature-provider").value, query: $("literature-query").value.trim(), limit: 5, public_confirmed: $("literature-public").checked})); });
$("model-form").addEventListener("submit", event => { event.preventDefault(); action(() => preview("model", {endpoint: $("model-endpoint").value.trim(), model: $("model-id").value.trim(), fields: JSON.parse($("model-context").value), public_confirmed: $("model-public").checked})); });
$("cancel-request").addEventListener("click", () => { $("request-dialog").close(); state.pending = null; $("model-key").value = ""; message("Request cancelled. No external request was sent."); });
$("request-dialog").addEventListener("cancel", () => { state.pending = null; $("model-key").value = ""; message("Request cancelled. No external request was sent."); });
$("approve-request").addEventListener("click", () => action(async () => { const pending = state.pending; if (!pending) return; $("request-dialog").close(); const body = {...pending.settings, project: requireProject(), approve_hash: pending.hash}; if (pending.kind === "model") { body.api_key = $("model-key").value; $("model-key").value = ""; } state.pending = null; const data = await api("/api/" + pending.kind + (pending.kind === "model" ? "/run" : "/retrieve"), body); accept(data, pending.kind === "model" ? "Received unverified model candidates. External evidence review is required." : "Retrieved publication identities. Statement entailment remains a separate review."); }));
$("review-file").addEventListener("change", () => action(async () => { const review = await fileJSON($("review-file")); if (!review) return; accept(await api("/api/review", {project: requireProject(), review}), "Recorded researcher review with explicit evidence and context states."); $("review-file").value = ""; }));
function executionSettings() {
  requireProject(); const kind = $("execution-kind").value; const assumptions = lines($("execution-assumptions").value);
  if (!assumptions.length) throw new Error("Specify the scientific assumptions before building or running a control.");
  if (!$("execution-control").value) throw new Error("No unexecuted reviewed control is available. Open a new project snapshot for another run.");
  const config = {kind, assumptions, random_seed: Number($("execution-seed").value), draws: Number($("execution-draws").value)};
  if (kind === "REFERENCE") { if (!$("execution-expected").value.trim()) throw new Error("Specify the independently expected difference before execution."); config.expected_difference = Number($("execution-expected").value); }
  return {project: state.project, control_id: $("execution-control").value, config};
}
$("execution-form").addEventListener("submit", event => { event.preventDefault(); action(async () => { const settings = executionSettings(); const file = $("numeric-file").files[0]; if (!file || file.size > 2 * 1024 * 1024) throw new Error("Choose a local numeric CSV no larger than 2 MiB."); settings.csv = await file.text(); accept(await api("/api/execute", settings), "Recorded the local control result and conservative scientific audit."); switchView("audit"); }); });
$("download-package").addEventListener("click", () => action(async () => { const data = await api("/api/package", executionSettings()); const bytes = Uint8Array.from(atob(data.package_base64), character => character.charCodeAt(0)); download(new Blob([bytes], {type: "application/zip"}), data.filename); accept(data, "Downloaded a reproducible execution package. The saved package includes its planned project snapshot."); }));
$("result-file").addEventListener("change", () => action(async () => { const result = await fileJSON($("result-file")); if (!result) return; accept(await api("/api/import-results", {project: requireProject(), result}), "Imported and checked the result against its execution plan."); $("result-file").value = ""; }));
window.addEventListener("beforeunload", event => { if (state.project) { event.preventDefault(); event.returnValue = ""; } });
fetch("/api/session").then(response => response.json()).then(data => {
  state.token = data.token; render();
  if (location.hash === "#demo=transcriptomics" || location.hash === "#demo=microscopy") {
    example(location.hash.endsWith("microscopy") ? "ml" : "rna");
    $("analysis-form").requestSubmit();
  }
}).catch(() => message("Local session could not be initialized. Reload the page.", true));
