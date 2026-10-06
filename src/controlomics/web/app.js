"use strict";
const state = {project: null, audit: [], token: null, pending: null, busy: false, profiles: [], narrative: null, reviewTemplate: null, evaluation: null, evaluationBundle: null, annotationHash: null, annotationDraft: null, annotationCase: null, revisions: []};
const $ = id => document.getElementById(id);
const lines = text => text.split(/\r?\n/).map(value => value.trim()).filter(Boolean);
const pairedBasis = "Complete-pair mean differences; independent pairs; sign-invariant differences for the permutation null; whole-pair resampling for the bootstrap.";
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
function accept(data, notice) { if (data.project) state.project = data.project; if (data.design_profiles) state.profiles = data.design_profiles; render(); message(notice); }
function options(select, entries) { const prior = select.value; select.replaceChildren(); for (const [value, label] of entries) { const option = node("option", label); option.value = value; select.append(option); } if (entries.some(entry => entry[0] === prior)) select.value = prior; }
function render() {
  const project = state.project;
  $("export-project").disabled = $("export-report").disabled = $("export-bundle").disabled = !project;
  for (const id of ["control-list", "evidence-list", "result-list", "audit-list", "execution-control", "claim-list", "design-profiles"]) $(id).replaceChildren();
  $("additional-claims").hidden = !project;
  $("add-control").disabled = $("check-methods").disabled = !project;
  if (!project) { for (const id of ["control-list", "evidence-list", "result-list", "audit-list"]) $(id).append(empty("Create or open a local project to inspect this section.")); return; }
  const controls = [...project.controls, ...project.candidates];
  const claims = project.claims.map(claim => [claim.claim_id, claim.statement]);
  for (const id of ["candidate-claim", "model-claim", "paired-claim"]) options($(id), claims);
  options($("review-control"), controls.map(control => [control.control_id, control.control_name + " / " + control.evidence_status]));
  for (const claim of project.claims) $("claim-list").append(field(claim.category + " / support " + claim.computational_support, claim.statement));
  for (const control of controls) {
    const card = node("article", undefined, "control-card"); const top = node("div", undefined, "card-top");
    top.append(node("span", control.control_class, "badge" + (control.control_class === "NEGATIVE" ? " negative" : "")), node("span", control.evidence_status, "evidence-state"));
    card.append(top, node("h3", control.control_name), field("Scientific rationale", control.scientific_rationale), field("Expected behavior", control.expected_behavior), field("Failure interpretation", control.failure_interpretation), field("Limitations", control.limitations.join(" ")));
    const details = node("details"); details.append(node("summary", "Inspect assumptions and provenance"), field("Method basis", control.method_basis), field("Uncertainties", control.uncertainties.join(" ")), field("Claim tested", control.claim_tested), field("Context compatibility", control.context_compatibility.status), field("Priority", control.priority + ": " + control.priority_rationale));
    const actions = node("div", undefined, "actions card-actions");
    if (project.candidates.some(item => item.control_id === control.control_id)) {
      const edit = node("button", "Edit specification", "small secondary"); edit.type = "button"; edit.addEventListener("click", () => editCandidate(control)); actions.append(edit);
    }
    const review = node("button", "Review evidence", "small secondary"); review.type = "button"; review.disabled = !project.evidence.some(item => item.existence_status === "VERIFIED");
    review.addEventListener("click", () => action(() => openReview(control.control_id))); actions.append(review);
    card.append(details, actions, node("div", control.scientific_level + " / " + control.execution_status, "card-foot")); $("control-list").append(card);
  }
  if (!controls.length) $("control-list").append(empty("No appropriate control was specified. Review the analysis context and recorded abstentions."));
  const paired = $("execution-adapter").value === "PAIRED_DIFFERENCE";
  for (const control of project.controls.filter(item => (paired ? item.scientific_level === "STATISTICAL" && item.control_class === "NULL" && item.method_basis === pairedBasis : item.scientific_level === "TECHNICAL" && ["POSITIVE", "NEGATIVE"].includes(item.control_class)) && ["METHOD_BASED", "EVIDENCE_BACKED"].includes(item.evidence_status) && !project.execution_plans.some(plan => plan.control_id === item.control_id))) {
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
  for (const profile of state.profiles) {
    const article = node("article", undefined, "panel"); article.append(node("h3", "Design interpretation"), field("Claim", project.claims.find(claim => claim.claim_id === profile.claim_id)?.statement), field("Provisional operations", profile.cues.map(cue => cue.facet.replaceAll("_", " ") + ": " + cue.basis).join("; ") || "No operation recognized."));
    for (const finding of profile.findings) article.append(field(finding.code, finding.message));
    article.append(field("Limits", profile.limitations.join(" "))); $("design-profiles").append(article);
  }
  $("ledger").textContent = JSON.stringify({provenance: project.provenance, network_audit: state.audit}, null, 2);
}
document.querySelectorAll(".tab").forEach(tab => tab.addEventListener("click", () => switchView(tab.dataset.view)));
$("analysis-form").addEventListener("submit", event => { event.preventDefault(); action(async () => {
  if (state.project && !window.confirm("Create a new project in this page? Export the current project and network ledger first if you want to keep them.")) { message("Kept the current project."); return; }
  const form = new FormData(event.target); const value = name => String(form.get(name) || "").trim();
  const context = {}; for (const key of ["organism", "tissue", "data_modality"]) if (value(key)) context[key] = value(key);
  const intake = {question: value("question"), analysis_description: value("analysis_description"), methods: lines(value("methods")), observed_result: value("observed_result"), claim: value("claim"), claim_category: value("claim_category"), computational_support: value("computational_support"), biological_context: context, design: {sampling_unit: value("sampling_unit") || null, data_partition: value("data_partition") || null}, assumptions: lines(value("assumptions"))};
  const data = await api("/api/analyze", {intake}); state.audit = []; accept(data, "Local design controls specified. Biological support and applicability remain unvalidated."); switchView("controls");
}); });
function example(kind) {
  const common = {organism: "Saccharomyces cerevisiae", tissue: "", assumptions: "This is a hypothetical development example, not observed biology.", sampling_unit: "Independent culture", data_partition: "Each culture is an independent unit."};
  const values = kind === "rna" ? {...common, question: "Does a hypothetical treatment change transcript abundance?", claim: "Transcript abundance differs between hypothetical conditions.", analysis_description: "A between-culture differential abundance comparison. The primary analysis was conducted separately.", methods: "Count-based differential abundance comparison", observed_result: "Hypothetical reported abundance differences; no measurements supplied.", claim_category: "COMPARATIVE", computational_support: "COMPARATIVE", data_modality: "bulk transcript counts"} : {...common, organism: "", question: "Can image features distinguish hypothetical cell morphology labels?", claim: "An image-feature classifier predicts morphology labels in new cultures.", analysis_description: "A supervised image-feature classifier evaluated on held-out cultures.", methods: "Image-feature classification", observed_result: "Hypothetical discrimination; no measured score supplied.", claim_category: "PREDICTIVE", computational_support: "PREDICTIVE", data_modality: "microscopy image features", data_partition: "All images from a culture remain in the same data partition."};
  for (const [name, value] of Object.entries(values)) $("analysis-form").elements.namedItem(name).value = value;
  switchView("analysis"); message("Loaded a hypothetical example. Review the fields, then create the control audit.");
}
$("example-rna").addEventListener("click", () => example("rna")); $("example-ml").addEventListener("click", () => example("ml"));
async function fileJSON(input) { const file = input.files[0]; if (!file) return null; if (file.size > 2 * 1024 * 1024) throw new Error("Local JSON exceeds the 2 MiB limit."); return (await api("/api/parse-json", {content: await file.text()})).value; }
$("project-file").addEventListener("change", () => action(async () => { const project = await fileJSON($("project-file")); if (!project) return; const data = await api("/api/analyze", {project}); state.audit = []; accept(data, "Opened and audited a local project. Review its evidence receipts before relying on them."); switchView("controls"); $("project-file").value = ""; }));
$("export-project").addEventListener("click", () => { if (state.project) download(JSON.stringify(state.project, null, 2), "project.controlomics.json"); });
$("export-audit").addEventListener("click", () => download(JSON.stringify(state.audit, null, 2), "network_audit.json"));
$("export-report").addEventListener("click", () => action(async () => { const report = await api("/api/report", {project: requireProject(), network_audit: state.audit}, true); download(report, "controlomics.report.html"); message("Downloaded the local report. Review it before sharing."); }));
$("export-bundle").addEventListener("click", () => action(async () => { const archive = await api("/api/review-bundle", {project: requireProject(), network_audit: state.audit, evaluation_bundle: state.evaluationBundle, annotation_revisions: state.revisions}, true); download(archive, "controlomics.review.zip"); message("Saved project, report, network ledger, and any loaded evaluation. Review descriptions before sharing."); }));
$("bundle-file").addEventListener("change", () => action(async () => { const file = $("bundle-file").files[0]; if (!file) return; if (file.size > 1024 * 1024) throw new Error("Review archives have a 1 MiB limit."); const bytes = new Uint8Array(await file.arrayBuffer()); let encoded = ""; for (let start = 0; start < bytes.length; start += 16384) encoded += String.fromCharCode(...bytes.subarray(start, start + 16384)); const data = await api("/api/open-bundle", {archive_base64: btoa(encoded)}); if ((state.project || state.evaluationBundle) && !window.confirm("Replace the current workspace with this validated bundle? Save the current review bundle first if needed.")) return; state.audit = data.network_audit_restored; state.revisions = data.annotation_revisions; state.evaluation = null; $("evaluation-result").replaceChildren(empty("No evaluation has been calculated.")); $("export-evaluation").disabled = true; await loadAnnotationBundle(data.evaluation_bundle, false); accept(data, "Restored validated local records. Hashes and reviewer identities are not authenticated; the ledger may be incomplete."); $("bundle-file").value = ""; switchView("controls"); }));
async function preview(kind, settings) { requireProject(); const result = await api("/api/" + kind + "/preview", settings); state.pending = {kind, settings, hash: result.approve_hash}; $("request-preview").textContent = JSON.stringify(result, null, 2); $("request-dialog").showModal(); message("No external request has been sent. Review the displayed payload."); }
$("literature-form").addEventListener("submit", event => { event.preventDefault(); action(() => preview("literature", {provider: $("literature-provider").value, query: $("literature-query").value.trim(), limit: 5, public_confirmed: $("literature-public").checked})); });
$("model-form").addEventListener("submit", event => { event.preventDefault(); action(async () => preview("model", {endpoint: $("model-endpoint").value.trim(), model: $("model-id").value.trim(), claim_id: $("model-claim").value, fields: (await api("/api/parse-json", {content: $("model-context").value})).value, public_confirmed: $("model-public").checked})); });
$("cancel-request").addEventListener("click", () => { $("request-dialog").close(); state.pending = null; $("model-key").value = ""; message("Request cancelled. No external request was sent."); });
$("request-dialog").addEventListener("cancel", () => { state.pending = null; $("model-key").value = ""; message("Request cancelled. No external request was sent."); });
$("approve-request").addEventListener("click", () => action(async () => { const pending = state.pending; if (!pending) return; $("request-dialog").close(); const body = {...pending.settings, project: requireProject(), approve_hash: pending.hash}; if (pending.kind === "model") { body.api_key = $("model-key").value; $("model-key").value = ""; } state.pending = null; const data = await api("/api/" + pending.kind + (pending.kind === "model" ? "/run" : "/retrieve"), body); accept(data, pending.kind === "model" ? "Received unverified model candidates. External evidence review is required." : "Retrieved publication identities. Statement entailment remains a separate review."); }));
$("review-file").addEventListener("change", () => action(async () => { const review = await fileJSON($("review-file")); if (!review) return; accept(await api("/api/review", {project: requireProject(), review}), "Recorded researcher review with explicit evidence and context states."); $("review-file").value = ""; }));
function executionSettings() {
  requireProject(); const kind = $("execution-kind").value; const assumptions = lines($("execution-assumptions").value);
  if (!assumptions.length) throw new Error("Specify the scientific assumptions before building or running a control.");
  if (!$("execution-control").value) throw new Error("No unexecuted reviewed control is available. Open a new project snapshot for another run.");
  const config = {kind, assumptions, adapter: $("execution-adapter").value, random_seed: Number($("execution-seed").value), draws: Number($("execution-draws").value)};
  if (config.adapter === "PAIRED_DIFFERENCE") { config.adapter_rationale = $("adapter-rationale").value.trim(); if (!config.adapter_rationale) throw new Error("Explain why the paired adapter applies to this specification."); }
  if (kind === "REFERENCE") { if (!$("execution-expected").value.trim()) throw new Error("Specify the independently expected difference before execution."); config.expected_difference = Number($("execution-expected").value); }
  return {project: state.project, control_id: $("execution-control").value, config};
}
$("execution-form").addEventListener("submit", event => { event.preventDefault(); action(async () => { const settings = executionSettings(); const file = $("numeric-file").files[0]; if (!file || file.size > 2 * 1024 * 1024) throw new Error("Choose a local numeric CSV no larger than 2 MiB."); settings.csv = await file.text(); accept(await api("/api/execute", settings), "Recorded the local control result and conservative scientific audit."); switchView("audit"); }); });
$("download-package").addEventListener("click", () => action(async () => { const data = await api("/api/package", executionSettings()); const bytes = Uint8Array.from(atob(data.package_base64), character => character.charCodeAt(0)); download(new Blob([bytes], {type: "application/zip"}), data.filename); accept(data, "Downloaded a reproducible execution package. The saved package includes its planned project snapshot."); }));
$("result-file").addEventListener("change", () => action(async () => { const result = await fileJSON($("result-file")); if (!result) return; accept(await api("/api/import-results", {project: requireProject(), result}), "Imported and checked the result against its execution plan."); $("result-file").value = ""; }));
const categories = ["DESCRIPTIVE", "ASSOCIATIONAL", "COMPARATIVE", "PREDICTIVE", "STATISTICAL", "FUNCTIONAL", "MECHANISTIC", "CAUSAL"];
for (const id of ["new-claim-category", "new-claim-support"]) options($(id), [["", "Choose a category"], ...categories.map(category => [category, category])]);
$("narrative-form").addEventListener("submit", event => { event.preventDefault(); action(async () => { const data = await api("/api/interpret", {description: $("narrative-description").value}); state.narrative = data.draft; $("narrative-preview").textContent = JSON.stringify(data.draft, null, 2); $("narrative-result").hidden = false; message("Drafted local fields. Review them and explicitly choose the claim and support categories."); }); });
$("use-narrative").addEventListener("click", () => { if (!state.narrative) return; const form = $("analysis-form"); for (const [name, value] of Object.entries(state.narrative.fields)) { const element = form.elements.namedItem(name); if (element) element.value = value; } for (const name of ["claim_category", "computational_support"]) if (!state.narrative.fields[name]) form.elements.namedItem(name).value = ""; message("Applied provisional fields. Complete missing values and review every field before creating a project."); });
$("claim-form").addEventListener("submit", event => { event.preventDefault(); action(async () => { const form = new FormData(event.target); const claim = {statement: form.get("statement"), category: form.get("category"), computational_support: form.get("computational_support"), assumptions: lines(String(form.get("assumptions") || ""))}; accept(await api("/api/add-claim", {project: requireProject(), claim}), "Added an explicit claim with its own design controls."); event.target.reset(); switchView("controls"); }); });
function editCandidate(control = null) {
  const form = $("candidate-form"); form.reset();
  if (control) { const values = {control_id: control.control_id, claim_id: control.claim_tested, name: control.control_name, control_class: control.control_class, scientific_level: control.scientific_level, rationale: control.scientific_rationale, expected_behavior: control.expected_behavior, failure_interpretation: control.failure_interpretation, method_basis: control.method_basis || "", priority: control.priority, priority_rationale: control.priority_rationale, uncertainties: control.uncertainties.join("\n"), limitations: control.limitations.join("\n")}; for (const [name, value] of Object.entries(values)) form.elements.namedItem(name).value = value; $("candidate-evidence").checked = control.evidence_required; }
  $("candidate-panel").open = true; $("candidate-panel").scrollIntoView({behavior: "smooth", block: "start"});
}
$("add-control").addEventListener("click", () => { requireProject(); editCandidate(); });
$("candidate-level").addEventListener("change", () => { if (["BIOLOGICAL", "MECHANISTIC"].includes($("candidate-level").value)) $("candidate-evidence").checked = true; });
$("candidate-form").addEventListener("submit", event => { event.preventDefault(); action(async () => { const form = new FormData(event.target); const value = name => String(form.get(name) || "").trim(); const control = {}; for (const name of ["name", "control_class", "scientific_level", "rationale", "expected_behavior", "failure_interpretation", "priority", "priority_rationale"]) control[name] = value(name); control.evidence_required = $("candidate-evidence").checked; control.method_basis = value("method_basis") || null; control.uncertainties = lines(value("uncertainties")); control.limitations = lines(value("limitations")); const specification = {claim_id: value("claim_id"), control, control_id: value("control_id") || null}; accept(await api("/api/specify-control", {project: requireProject(), specification}), "Saved an unverified researcher specification. Complete evidence review before relying on it."); $("candidate-panel").open = false; }); });
$("check-methods").addEventListener("click", () => action(async () => accept(await api("/api/method-review", {project: requireProject()}), "Reviewed technical and statistical specifications with method bases. This does not establish empirical validity.")));
async function openReview(controlId) {
  switchView("evidence"); $("review-control").value = controlId;
  const data = await api("/api/review-template", {project: requireProject(), control_id: controlId}); state.reviewTemplate = data.template;
  $("statement-reviews").replaceChildren(); $("human-attestation").checked = $("supersede-review").checked = false; $("supersede-review-label").hidden = !data.template.supersedes_review_sha256;
  const sourceOptions = state.project.evidence.filter(item => item.existence_status === "VERIFIED").map(item => [item.evidence_id, item.title || item.evidence_id]);
  for (const [index, statement] of data.template.statements.entries()) {
    const panel = node("fieldset", undefined, "statement-panel"); panel.append(node("legend", index === 0 ? "Rationale support" : "Expected behavior support"), field("Exact statement", statement));
    function input(label, suffix, type = "textarea") { const wrapper = node("label", label); const element = node(type); element.id = "statement-" + index + "-" + suffix; element.required = true; if (type === "textarea") element.rows = 3; wrapper.append(element); panel.append(wrapper); return element; }
    options(input("Publication identity", "evidence", "select"), sourceOptions);
    options(input("Relationship", "relationship", "select"), [["UNCERTAIN", "UNCERTAIN"], ["SUPPORTS", "SUPPORTS"], ["CONTRADICTS", "CONTRADICTS"]]);
    input("Locally supplied source text", "source"); const excerpt = input("Excerpt present in that text, at most 300 characters", "excerpt"); excerpt.maxLength = 300;
    input("Source locator", "locator", "input"); input("Scientific explanation of the relationship", "rationale"); const context = input("Context established by the source, as JSON", "context"); context.value = "{}";
    $("statement-reviews").append(panel);
  }
  $("review-panel").open = true; $("review-panel").scrollIntoView({behavior: "smooth", block: "start"}); message("Review the exact statements against source text. No review has been recorded yet.");
}
$("review-control").addEventListener("change", () => action(() => openReview($("review-control").value)));
$("human-review-form").addEventListener("submit", event => { event.preventDefault(); action(async () => {
  const template = state.reviewTemplate; if (!template || template.control_id !== $("review-control").value) throw new Error("Open the selected control's review first.");
  if (!$("human-attestation").checked) throw new Error("A real researcher must attest this source review.");
  if (template.supersedes_review_sha256 && !$("supersede-review").checked) throw new Error("Explicitly approve replacement of the prior review or keep the previous record.");
  const statements = []; for (const [index, statement] of template.statements.entries()) { const value = suffix => $("statement-" + index + "-" + suffix).value.trim(); statements.push({evidence_id: value("evidence"), statement, relationship: value("relationship"), source_text: value("source"), excerpt: value("excerpt"), locator: value("locator"), rationale: value("rationale"), source_context: (await api("/api/parse-json", {content: value("context")})).value}); }
  const review = {control_id: template.control_id, reviewer: $("review-researcher").value.trim(), statements, limitations: lines($("review-limitations").value), supersedes_review_sha256: template.supersedes_review_sha256};
  accept(await api("/api/review", {project: requireProject(), review}), "Recorded a researcher attestation with explicit evidence and context outcomes."); state.reviewTemplate = null; $("statement-reviews").replaceChildren(); $("human-attestation").checked = false; $("review-panel").open = false; switchView("controls");
}); });
$("evaluation-form").addEventListener("submit", event => { event.preventDefault(); action(async () => {
  if ($("evaluation-file").files[0]) await loadAnnotationBundle(await fileJSON($("evaluation-file")));
  if (!state.evaluationBundle) throw new Error("Choose a local evaluation bundle first.");
  const data = await api("/api/evaluate", {bundle: state.evaluationBundle, partition: $("evaluation-partition").value || null}); state.evaluation = data.evaluation;
  const report = data.evaluation, container = $("evaluation-result"); container.replaceChildren();
  const overview = node("article", undefined, "panel"); overview.append(node("h3", report.dataset_id), field("Provider and partition", report.provider + " / " + report.partition), field("Annotation origins", "References: " + report.reference_origin + "; judgments: " + report.judgment_origin), field("Coverage", report.coverage.cases + " cases, " + report.coverage.recommendations + " recommendations, " + report.coverage.appropriateness_assessed + " assessed for appropriateness, " + report.coverage.uncertain_or_missing_appropriateness + " uncertain or missing.")); container.append(overview);
  const panel = node("div", undefined, "panel metric-panel"), table = node("table"), head = node("thead"), header = node("tr"); for (const label of ["Metric", "Result", "Denominator", "Definition"]) header.append(node("th", label)); head.append(header); table.append(head);
  const body = node("tbody"); for (const [name, metric] of Object.entries(report.metrics)) { const row = node("tr"); row.append(node("td", name.replaceAll("_", " ")), node("td", metric.value === null ? "Unavailable" : String(Number(metric.value.toFixed(4)))), node("td", String(metric.denominator)), node("td", metric.definition)); [...row.children].forEach((cell, index) => { cell.dataset.label = ["Metric", "Result", "Denominator", "Definition"][index]; }); body.append(row); } table.append(body); panel.append(table); container.append(panel);
  const limits = node("article", undefined, "panel"); limits.append(field("Limitations", report.limitations.join(" ")), field("Interval interpretation", "The exported JSON includes descriptive Wilson intervals. Correlated cases and controls require a separate inferential design.")); container.append(limits);
  $("export-evaluation").disabled = false; message("Calculated local metrics with explicit denominators. Unassessed scientific quality remains unavailable.");
}); });
$("export-evaluation").addEventListener("click", () => { if (state.evaluation) download(JSON.stringify(state.evaluation, null, 2), "controlomics.evaluation.json"); });
$("execution-adapter").addEventListener("change", () => { const paired = $("execution-adapter").value === "PAIRED_DIFFERENCE"; $("adapter-rationale-label").hidden = !paired; $("adapter-rationale").required = paired; $("execution-kind").options[0].disabled = paired; if (paired && $("execution-kind").value === "REFERENCE") $("execution-kind").value = "PERMUTATION"; $("csv-layout").textContent = paired ? "CSV columns: pair,condition,value. Exactly one value for condition 0 and 1 per pair, 2 to 1,000 complete pairs. Pair identifiers do not establish independence across pairs." : "CSV columns: unit,label,value. Unique unit IDs, labels 0 or 1, at least two units per group, maximum 2,000 rows. Input remains on this computer."; render(); });
$("paired-form").addEventListener("submit", event => { event.preventDefault(); action(async () => { accept(await api("/api/specify-paired", {project: requireProject(), claim_id: $("paired-claim").value, rationale: $("paired-rationale").value.trim(), assumptions: lines($("paired-assumptions").value)}), "Specified a paired statistical control. Researcher-supplied assumptions still need justification."); $("execution-adapter").value = "PAIRED_DIFFERENCE"; $("execution-adapter").dispatchEvent(new Event("change")); }); });
async function loadAnnotationBundle(bundle, resetRevisions = true) {
  const data = bundle ? await api("/api/annotation-template", {bundle}) : null;
  state.evaluationBundle = data?.bundle || null; state.annotationHash = data?.bundle_sha256 || null;
  state.annotationDraft = data ? structuredClone(data.bundle) : null; state.annotationCase = null;
  if (resetRevisions) state.revisions = [];
  $("annotation-panel").hidden = !data; $("export-evaluation-bundle").disabled = !data; $("export-revisions").disabled = !data;
  $("annotation-attestation").checked = false; $("annotation-reviewer").value = ""; $("annotation-origin").value = ""; $("evaluation-file").value = "";
  if (!data) return;
  for (const prediction of state.annotationDraft.predictions.cases) for (const control of prediction.controls) {
    if (!state.annotationDraft.judgments.some(item => item.case_id === prediction.case_id && item.control_id === control.control_id)) state.annotationDraft.judgments.push({case_id: prediction.case_id, control_id: control.control_id, appropriate: null, unsupported: null, matched_reference_ids: [], rationale: "No judgment recorded."});
  }
  options($("annotation-case"), data.bundle.dataset.cases.map(item => [item.case_id, item.case_id + ": " + item.description]));
  renderAnnotationCase();
}
function annotationBoolean(label, id, value, parent) { const wrapper = node("label", label), select = node("select"); select.id = id; options(select, [["", "Unknown"], ["true", "Yes"], ["false", "No"]]); select.value = value === null ? "" : String(value); wrapper.append(select); parent.append(wrapper); return select; }
function annotationText(label, id, value, parent) { const wrapper = node("label", label), input = node("textarea"); input.id = id; input.rows = 2; input.required = true; input.maxLength = 12000; input.value = value; wrapper.append(input); parent.append(wrapper); }
function saveAnnotationCase() {
  if (!state.annotationCase || !state.annotationDraft) return;
  const bool = id => $(id).value === "" ? null : $(id).value === "true";
  const judgments = state.annotationDraft.judgments.filter(item => item.case_id === state.annotationCase);
  judgments.forEach((item, index) => { item.appropriate = bool("ann-appropriate-" + index); item.unsupported = bool("ann-unsupported-" + index); item.rationale = $("ann-rationale-" + index).value.trim(); item.matched_reference_ids = item.appropriate === true ? [...$("ann-matches-" + index).querySelectorAll("input:checked")].map(input => input.value) : []; });
  state.annotationDraft.evidence_decisions.filter(item => item.case_id === state.annotationCase).forEach((item, index) => { item.reference_decision = bool("ann-evidence-" + index); item.rationale = $("ann-evidence-rationale-" + index).value.trim(); });
}
function renderAnnotationCase() {
  const bundle = state.annotationDraft; if (!bundle) return;
  state.annotationCase = $("annotation-case").value;
  const current = bundle.dataset.cases.find(item => item.case_id === state.annotationCase), prediction = bundle.predictions.cases.find(item => item.case_id === current.case_id);
  $("annotation-case-info").replaceChildren(field("Case and partition", current.description + " / " + current.partition), field("Reference origin", bundle.dataset.annotation_origin), field("Reference definitions", current.references.map(item => item.reference_id + ": " + item.description + (item.essential ? " (essential)" : "")).join("; ") || "No references supplied"), field("Prediction", prediction.abstained ? "Explicit abstention" : prediction.findings.join("; ") || "No finding codes supplied"));
  $("annotation-controls").replaceChildren(); $("annotation-evidence").replaceChildren();
  bundle.judgments.filter(item => item.case_id === current.case_id).forEach((item, index) => {
    const control = prediction.controls.find(control => control.control_id === item.control_id), panel = node("fieldset", undefined, "statement-panel"); panel.append(node("legend", control.control_class + " / " + control.scientific_level), field("Recommendation", control.description));
    const grid = node("div", undefined, "grid"), appropriate = annotationBoolean("Appropriate for this case", "ann-appropriate-" + index, item.appropriate, grid); annotationBoolean("Unsupported recommendation", "ann-unsupported-" + index, item.unsupported, grid); panel.append(grid);
    const matches = node("div"); matches.id = "ann-matches-" + index; matches.append(node("p", "References covered, only for appropriate recommendations"));
    for (const reference of current.references) { const label = node("label", undefined, "check"), checkbox = node("input"); checkbox.type = "checkbox"; checkbox.value = reference.reference_id; checkbox.checked = item.matched_reference_ids.includes(reference.reference_id); checkbox.disabled = appropriate.value !== "true"; label.append(checkbox, node("span", reference.reference_id + ": " + reference.description)); matches.append(label); }
    appropriate.addEventListener("change", () => matches.querySelectorAll("input").forEach(input => { input.disabled = appropriate.value !== "true"; if (input.disabled) input.checked = false; })); panel.append(matches); annotationText("Reason for the supplied judgments", "ann-rationale-" + index, item.rationale, panel); $("annotation-controls").append(panel);
  });
  bundle.evidence_decisions.filter(item => item.case_id === current.case_id).forEach((item, index) => { const panel = node("fieldset", undefined, "statement-panel"); panel.append(node("legend", item.layer), field("Imported prediction", item.unit_id + ": " + item.predicted_decision)); annotationBoolean("Reference decision", "ann-evidence-" + index, item.reference_decision, panel); annotationText("Reason for the evidence reference judgment", "ann-evidence-rationale-" + index, item.rationale, panel); $("annotation-evidence").append(panel); });
}
$("annotation-case").addEventListener("change", () => { saveAnnotationCase(); renderAnnotationCase(); });
$("open-annotations").addEventListener("click", () => action(async () => { if ($("evaluation-file").files[0]) await loadAnnotationBundle(await fileJSON($("evaluation-file"))); if (!state.evaluationBundle) throw new Error("Choose a local evaluation bundle first."); $("annotation-panel").open = true; $("annotation-panel").scrollIntoView({block: "start"}); message("Opened imported recommendations and reference definitions. No new judgments have been recorded."); }));
$("annotation-form").addEventListener("submit", event => { event.preventDefault(); action(async () => { saveAnnotationCase(); if (!$("annotation-attestation").checked) throw new Error("A real reviewer must attest the judgments."); const submission = {bundle_sha256: state.annotationHash, judgment_origin: $("annotation-origin").value, annotator: $("annotation-reviewer").value.trim(), human_attested: true, judgments: state.annotationDraft.judgments, evidence_decisions: state.annotationDraft.evidence_decisions}; const data = await api("/api/annotate", {bundle: state.evaluationBundle, submission}); state.revisions.push(data.revision); await loadAnnotationBundle(data.bundle, false); state.evaluation = null; $("evaluation-result").replaceChildren(empty("Judgments changed. Calculate the current snapshot to see updated metrics.")); $("export-evaluation").disabled = true; message("Recorded supplied judgments and snapshot hashes. Export this bundle and revisions; identities remain unauthenticated."); }); });
$("export-evaluation-bundle").addEventListener("click", () => { if (state.evaluationBundle) download(JSON.stringify(state.evaluationBundle, null, 2), "controlomics.annotations.json"); });
$("export-revisions").addEventListener("click", () => download(JSON.stringify(state.revisions, null, 2), "controlomics.annotation_revisions.json"));
window.addEventListener("beforeunload", event => { if (state.project || state.evaluationBundle) { event.preventDefault(); event.returnValue = ""; } });
fetch("/api/session").then(response => response.json()).then(data => {
  state.token = data.token; render();
  if (location.hash === "#demo=transcriptomics" || location.hash === "#demo=microscopy") {
    example(location.hash.endsWith("microscopy") ? "ml" : "rna");
    $("analysis-form").requestSubmit();
  }
}).catch(() => message("Local session could not be initialized. Reload the page.", true));
