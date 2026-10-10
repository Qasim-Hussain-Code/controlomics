"use strict";
const state = {project: null, audit: [], token: null, pending: null, busy: false, focusAfterAction: null, profiles: [], narrative: null, reviewTemplate: null, evaluation: null, evaluationBundle: null, annotationHash: null, annotationDraft: null, annotationCase: null, revisions: [], view: "analysis", inputSummary: null, revision: 0, preparedRevision: 0, drafts: new Set(), formBaselines: new Map()};
const $ = id => document.getElementById(id);
const lines = text => text.split(/\r?\n/).map(value => value.trim()).filter(Boolean);
const pairedBasis = "Complete-pair mean differences; independent pairs; sign-invariant differences for the permutation null; whole-pair resampling for the bootstrap.";
function message(text, error = false) { $("status").textContent = text; $("status").className = error ? "status error" : state.busy ? "status busy" : "status"; $("status").setAttribute("role", error ? "alert" : "status"); $("status").setAttribute("aria-live", error ? "assertive" : "polite"); if (error) $("status").scrollIntoView({block: "nearest", behavior: "instant"}); }
function focusDestination(element) { if (state.busy) state.focusAfterAction = element; else element?.focus({preventScroll: true}); }
function lockInputs(locked) { document.querySelectorAll("form, .file-label").forEach(element => { element.inert = locked; }); }
async function action(work) {
  if (state.busy) return;
  const previousFocus = document.activeElement;
  state.busy = true; state.focusAfterAction = null; lockInputs(true); $("workspace-main").setAttribute("aria-busy", "true"); message("Processing the requested operation...");
  try { await work(); } catch (error) { message(error.message || "Operation failed.", true); }
  finally {
    state.busy = false; lockInputs(false); $("status").classList.remove("busy"); $("workspace-main").setAttribute("aria-busy", "false");
    const destination = state.focusAfterAction; state.focusAfterAction = null;
    if (destination?.isConnected && destination.checkVisibility()) destination.focus({preventScroll: true});
    else if (document.activeElement === document.body && previousFocus?.isConnected && !previousFocus.disabled && previousFocus.checkVisibility()) previousFocus.focus({preventScroll: true});
  }
}
async function refreshSession() {
  const response = await fetch("/api/session", {signal: AbortSignal.timeout(10000)});
  if (!response.ok) throw new Error("Local session is unavailable. Keep this page open to retain unexported work.");
  const data = await response.json();
  if (typeof data.token !== "string" || !/^[A-Za-z0-9_-]{32,128}$/.test(data.token)) throw new Error("Invalid local session response.");
  state.token = data.token;
}
async function api(path, body, binary = false) {
  if (!state.token) throw new Error("Local session is not ready. Reload the page.");
  const payload = JSON.stringify(body);
  if (new TextEncoder().encode(payload).length > 2 * 1024 * 1024) throw new Error("The local request exceeds 2 MiB including formatting and the project snapshot. Use the CLI for inputs near the file-size limit.");
  let response;
  try { response = await fetch(path, {method: "POST", headers: {"Content-Type": "application/json", "X-Controlomics-Token": state.token}, body: payload, signal: AbortSignal.timeout(90000)}); }
  catch {
    throw new Error("The local response was interrupted. Keep this page open to retain your work. No automatic retry was made." + (/\/api\/(model\/run|literature\/retrieve)$/.test(path) ? " The approved external request may already have been transmitted; its ledger may be unavailable." : ""));
  }
  if (response.status === 403) {
    const previousToken = state.token;
    try { await refreshSession(); } catch { throw new Error("Local authorization could not be renewed. Keep this page open and retain exports before reloading."); }
    if (state.token !== previousToken) throw new Error("The local server session was renewed. Your workspace is retained. Retry the operation; external requests require a new preview and approval.");
  }
  if (binary && response.ok) return response.blob();
  let data;
  try { data = await response.json(); } catch { throw new Error("The local response was incomplete or invalid. Your workspace is retained; no automatic retry was made."); }
  if (data.network_audit?.length) { state.audit.push(...data.network_audit); recordChange(); }
  if (!response.ok || data.error) { render(); throw new Error(data.error || "Operation failed."); }
  return data;
}
function requireProject() { if (!state.project) throw new Error("Create or open a project first."); return state.project; }
function renderSaveState() {
  const hasRecords = Boolean(state.project || state.evaluationBundle), unprepared = hasRecords && state.revision !== state.preparedRevision;
  $("save-state").textContent = state.drafts.size ? "Unrecorded inputs" : unprepared ? "Export needed" : hasRecords ? "Bundle prepared" : "Local workspace";
  $("save-state").dataset.state = state.drafts.size || unprepared ? "pending" : "local";
  $("overview-save-state").textContent = $("save-state").textContent; $("overview-save-state").dataset.state = $("save-state").dataset.state;
  $("save-state").title = "Records stay in browser memory. A prepared download must be retained separately. Unrecorded form edits and raw inputs are not included in review bundles.";
}
function recordChange() { state.revision++; renderSaveState(); }
function formSignature(form) {
  if (form.id === "annotation-form" && state.annotationDraft) {
    saveAnnotationCase();
    return JSON.stringify([$("annotation-origin").value, $("annotation-reviewer").value, $("annotation-attestation").checked, state.annotationDraft.judgments, state.annotationDraft.evidence_decisions]);
  }
  return JSON.stringify([...form.elements].filter(element => element.type !== "password" && !["submit", "button"].includes(element.type)).map(element => [element.id || element.name, element.type === "file" ? [...element.files].map(file => [file.name, file.size, file.lastModified]) : ["checkbox", "radio"].includes(element.type) ? element.checked : element.value]));
}
function trackForm(form) { if (formSignature(form) === state.formBaselines.get(form.id)) state.drafts.delete(form.id); else state.drafts.add(form.id); renderSaveState(); }
function rememberForms() { queueMicrotask(() => document.querySelectorAll("form").forEach(form => state.formBaselines.set(form.id, formSignature(form)))); }
function clearDraft(id) { state.drafts.delete(id); queueMicrotask(() => state.formBaselines.set(id, formSignature($(id)))); renderSaveState(); }
function hasUnsavedWork() { return state.busy || state.drafts.size > 0 || Boolean(state.project || state.evaluationBundle) && state.revision !== state.preparedRevision; }
function confirmReplacement() { return !state.project && !state.evaluationBundle && !state.drafts.size || window.confirm("Replace the current workspace and its form inputs? Prepare and retain a review bundle first to keep recorded work. Unrecorded inputs are not included in bundles."); }
function fillAnalysis(project) {
  const analysis = project.analysis, claim = project.claims[0], context = analysis.biological_context;
  const values = {question: analysis.scientific_question, analysis_description: analysis.analysis_description, methods: analysis.methods.join("\n"), observed_result: analysis.observed_result, claim: claim.statement, claim_category: claim.category, computational_support: claim.computational_support, assumptions: claim.assumptions.join("\n"), sampling_unit: analysis.design.sampling_unit || "", data_partition: analysis.design.data_partition || "", organism: context.organism || "", tissue: context.tissue || "", data_modality: context.data_modality || ""};
  for (const [name, value] of Object.entries(values)) $("analysis-form").elements.namedItem(name).value = value;
}
function resetWorkspace() {
  Object.assign(state, {project: null, audit: [], pending: null, profiles: [], narrative: null, reviewTemplate: null, evaluation: null, evaluationBundle: null, annotationHash: null, annotationDraft: null, annotationCase: null, revisions: []});
  document.querySelectorAll("form").forEach(form => form.reset()); state.drafts.clear();
  for (const id of ["project-file", "bundle-file", "review-file", "result-file", "evaluation-file"]) $(id).value = "";
  for (const id of ["candidate-claim", "model-claim", "paired-claim", "review-control", "annotation-case"]) $(id).replaceChildren();
  $("narrative-result").hidden = true; $("narrative-preview").textContent = "";
  $("statement-reviews").replaceChildren(); $("review-panel").open = false; $("candidate-panel").open = false;
  $("annotation-panel").hidden = true; $("annotation-panel").open = false;
  for (const id of ["annotation-case-info", "annotation-controls", "annotation-evidence"]) $(id).replaceChildren();
  for (const id of ["export-evaluation", "export-evaluation-bundle", "export-revisions"]) $(id).disabled = true;
  $("evaluation-result").replaceChildren(empty("No evaluation has been calculated."));
  $("control-search").value = $("control-class-filter").value = $("control-claim-filter").value = $("control-state-filter").value = "";
  $("model-key").value = ""; $("request-preview").textContent = ""; $("ledger").textContent = "";
  if ($("request-dialog").open) $("request-dialog").close();
  clearInputSummary(); syncExecutionFields(); state.revision++; state.preparedRevision = state.revision;
  rememberForms();
}
const viewNames = {analysis: "Analysis & claims", controls: "Controls", evidence: "Evidence library", execution: "Execution", audit: "Scientific audit", evaluation: "Evaluation"};
const mobileNavigation = window.matchMedia("(max-width:760px)");
function syncNavigation() { $("workspace-tabs").setAttribute("aria-orientation", "vertical"); const open = mobileNavigation.matches && document.body.classList.contains("nav-open"); $("nav-toggle").setAttribute("aria-expanded", String(open)); $("nav-toggle").setAttribute("aria-label", open ? "Close navigation" : "Open navigation"); $("workspace-nav").inert = mobileNavigation.matches && !open; $("workspace-canvas").inert = open; $("workspace-header").inert = open; if (mobileNavigation.matches) $("workspace-nav").setAttribute("aria-hidden", String(!open)); else $("workspace-nav").removeAttribute("aria-hidden"); if (open) { $("workspace-nav").setAttribute("role", "dialog"); $("workspace-nav").setAttribute("aria-modal", "true"); } else { $("workspace-nav").removeAttribute("role"); $("workspace-nav").removeAttribute("aria-modal"); } }
function closeNavigation(returnFocus = false) { document.body.classList.remove("nav-open"); syncNavigation(); if (returnFocus) $("nav-toggle").focus(); }
function switchView(name, closeMenu = true) { if (!viewNames[name]) return; const changed = state.view !== name; state.view = name; document.querySelectorAll(".view").forEach(view => { view.hidden = view.id !== "view-" + name; view.tabIndex = view.hidden ? -1 : 0; }); document.querySelectorAll(".tab").forEach(tab => { const selected = tab.dataset.view === name; tab.classList.toggle("active", selected); tab.setAttribute("aria-selected", String(selected)); tab.tabIndex = selected ? 0 : -1; }); $("current-section").textContent = viewNames[name]; document.title = viewNames[name] + " | Controlomics"; if (changed) $("view-" + name).scrollIntoView({block: "start", behavior: "instant"}); if (closeMenu && document.body.classList.contains("nav-open")) { closeNavigation(); $("workspace-main").focus({preventScroll: true}); } }
function node(tag, text, className) { const element = document.createElement(tag); if (text !== undefined) element.textContent = text; if (className) element.className = className; return element; }
function field(label, value) { const wrapper = node("div", undefined, "field"); wrapper.append(node("strong", label), node("p", value || "Not supplied")); return wrapper; }
function empty(text) { return node("p", text, "empty"); }
function download(content, filename, type = "application/json") { const blob = content instanceof Blob ? content : new Blob([content], {type}); const url = URL.createObjectURL(blob); const anchor = node("a"); anchor.href = url; anchor.download = filename; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
function accept(data, notice) { const changedProject = data.project && state.project?.manifest.project_id !== data.project.manifest.project_id; if (data.project) { if (changedProject) { $("control-search").value = ""; $("control-class-filter").value = $("control-claim-filter").value = $("control-state-filter").value = ""; $("execution-control").value = ""; fillAnalysis(data.project); } state.project = data.project; recordChange(); } if (data.design_profiles) state.profiles = data.design_profiles; document.querySelectorAll(".workspace-menu[open]").forEach(menu => { menu.open = false; }); render(); if (changedProject) rememberForms(); message(notice); }
function options(select, entries) { const prior = select.value; select.replaceChildren(); for (const [value, label] of entries) { const option = node("option", label); option.value = value; select.append(option); } if (entries.some(entry => entry[0] === prior)) select.value = prior; }
function renderOverview() {
  const project = state.project, controls = project ? [...project.controls, ...project.candidates] : [];
  const counts = {claims: project?.claims.length || 0, controls: controls.length, evidence: project?.evidence.length || 0, results: project?.results.filter(item => item.execution_status === "COMPLETED").length || 0};
  for (const [key, value] of Object.entries(counts)) { $("metric-" + key).textContent = String(value); $("nav-" + key).textContent = String(value); }
  $("control-search").disabled = $("control-class-filter").disabled = $("control-claim-filter").disabled = $("control-state-filter").disabled = !project;
  $("reset-control-filters").disabled = !project;
  $("review-prerequisite").hidden = !project || project.evidence.some(item => item.existence_status === "VERIFIED");
  $("claim-filter-label").hidden = !project || project.claims.length < 2;
  options($("control-claim-filter"), [["", "All scientific claims"], ...(project?.claims || []).map(claim => [claim.claim_id, claim.statement])]);
  $("control-visible-count").textContent = counts.controls + " specifications";
  document.querySelector(".workspace-overview").classList.toggle("has-project", Boolean(project));
  $("project-kicker").textContent = project ? "Scientific question" : "Scientific control workspace";
  $("project-title").textContent = project ? project.analysis.scientific_question : "No project open";
  $("project-title").title = project ? project.analysis.scientific_question : "";
  $("project-subtitle").hidden = Boolean(project);
  $("project-subtitle").textContent = project ? "Analysis record. Review states and scientific limitations are recorded separately." : "Create an analysis record or open a saved project.";
  $("project-identifier").hidden = !project;
  $("project-identifier").textContent = project ? "Project: " + project.manifest.project_id : "";
  $("project-meta").textContent = project ? "Methods: " + project.analysis.methods.join("; ") : "Local records of claims, controls, evidence, and execution.";
  $("metric-claims-note").textContent = project ? counts.claims === 1 ? project.claims[0].category.toLowerCase() + " claim" : "Claims in the current analysis" : "Awaiting a project";
  $("metric-controls-note").textContent = project ? project.candidates.length ? project.candidates.length + " unreviewed candidate" + (project.candidates.length === 1 ? "" : "s") : "Review states recorded separately" : "No controls recorded";
  const identities = project?.evidence.filter(item => item.existence_status === "VERIFIED").length || 0;
  $("metric-evidence-note").textContent = project?.evidence.length ? identities + " recorded identity check" + (identities === 1 ? "" : "s") : "Identity and support are separate";
  $("metric-results-note").textContent = counts.results ? "Execution does not establish validity" : "No completed executions";
}
function renderControlCards() {
  const project = state.project; if (!project) return;
  const controls = [...project.controls, ...project.candidates], term = $("control-search").value.trim().toLocaleLowerCase(), selectedClass = $("control-class-filter").value, selectedClaim = $("control-claim-filter").value, selectedState = $("control-state-filter").value;
  const visible = controls.filter(control => (!selectedState || control.evidence_status === selectedState) && (!selectedClaim || control.claim_tested === selectedClaim) && (!selectedClass || control.control_class === selectedClass) && (!term || [control.control_name, control.scientific_rationale, control.expected_behavior, control.control_id, project.claims.find(claim => claim.claim_id === control.claim_tested)?.statement || ""].join(" ").toLocaleLowerCase().includes(term)));
  $("reset-control-filters").disabled = !term && !selectedClass && !selectedClaim && !selectedState;
  $("control-list").replaceChildren(); $("control-visible-count").textContent = visible.length === controls.length ? controls.length + " specification" + (controls.length === 1 ? "" : "s") : visible.length + " of " + controls.length + " specifications";
  for (const control of visible) {
    const card = node("article", undefined, "control-card control-record"), top = node("div", undefined, "card-top"), evidenceState = node("span", control.evidence_status, "evidence-state");
    card.dataset.controlClass = control.control_class; evidenceState.dataset.state = control.evidence_status;
    top.append(node("span", control.control_class, "badge" + (control.control_class === "NEGATIVE" ? " negative" : "")), evidenceState, node("span", "Priority: " + control.priority.toLowerCase(), "record-priority"));
    const heading = node("div", undefined, "record-heading");
    heading.append(node("span", "C" + String(controls.indexOf(control) + 1).padStart(2, "0"), "control-index"), node("h3", control.control_name));
    card.append(top, heading, field("Claim tested", project.claims.find(claim => claim.claim_id === control.claim_tested).statement), field("Scientific rationale", control.scientific_rationale), field("Expected behavior", control.expected_behavior), field("Failure interpretation", control.failure_interpretation), field("Limitations", control.limitations.join(" ")));
    const details = node("details"); details.append(node("summary", "Assumptions & provenance"), field("Control identifier", control.control_id), field("Method basis", control.method_basis), field("Uncertainties", control.uncertainties.join(" ")), field("Claim tested", project.claims.find(claim => claim.claim_id === control.claim_tested).statement), field("Claim identifier", control.claim_tested), field("Context compatibility", control.context_compatibility.status), field("Priority", control.priority + ": " + control.priority_rationale));
    const actions = node("div", undefined, "actions card-actions");
    if (project.candidates.some(item => item.control_id === control.control_id)) { const edit = node("button", "Edit specification", "small secondary"); edit.type = "button"; edit.addEventListener("click", () => editCandidate(control)); actions.append(edit); }
    const review = node("button", "Review evidence", "small secondary"); review.type = "button"; review.disabled = !project.evidence.some(item => item.existence_status === "VERIFIED"); if (review.disabled) review.setAttribute("aria-describedby", "review-prerequisite"); review.addEventListener("click", () => action(() => openReview(control.control_id))); actions.append(review);
    const foot = node("div", undefined, "card-foot"), execution = node("span", control.execution_status.replaceAll("_", " "), "execution-chip"); execution.dataset.status = control.execution_status; foot.append(node("span", control.scientific_level + " CONTROL"), execution);
    card.append(details, actions, foot); $("control-list").append(card);
  }
  if (!visible.length) $("control-list").append(empty(controls.length ? "No controls match this search. Try another term or reset the filters." : "No appropriate control was specified. Review the analysis context and recorded abstentions."));
}
function render() {
  const project = state.project;
  renderOverview();
  renderSaveState();
  $("export-project").disabled = $("export-report").disabled = $("export-bundle").disabled = !project;
  for (const id of ["control-list", "evidence-list", "result-list", "audit-list", "claim-list", "design-profiles"]) $(id).replaceChildren();
  $("additional-claims").hidden = !project;
  $("add-control").disabled = $("check-methods").disabled = !project;
  if (!project) { options($("execution-control"), [["", "Select a reviewed control"]]); updateExecutionAvailability(); for (const id of ["control-list", "evidence-list", "result-list", "audit-list"]) $(id).append(empty("Create or open a local project to inspect this section.")); return; }
  const controls = [...project.controls, ...project.candidates];
  const claims = project.claims.map(claim => [claim.claim_id, claim.statement]);
  for (const id of ["candidate-claim", "model-claim", "paired-claim"]) options($(id), claims);
  options($("review-control"), controls.map(control => [control.control_id, control.control_name + " / " + control.evidence_status]));
  for (const claim of project.claims) $("claim-list").append(field(claim.category + " / support " + claim.computational_support, claim.statement));
  renderControlCards();
  const paired = $("execution-adapter").value === "PAIRED_DIFFERENCE";
  const eligible = project.controls.filter(item => (paired ? item.scientific_level === "STATISTICAL" && item.control_class === "NULL" && item.method_basis === pairedBasis : item.scientific_level === "TECHNICAL" && ["POSITIVE", "NEGATIVE"].includes(item.control_class)) && ["METHOD_BASED", "EVIDENCE_BACKED"].includes(item.evidence_status) && !project.execution_plans.some(plan => plan.control_id === item.control_id));
  options($("execution-control"), [["", "Select a reviewed control"], ...eligible.map(control => [control.control_id, control.control_class + ": " + control.control_name])]);
  updateExecutionAvailability();
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
    const control = controls.find(item => item.control_id === result.control_id), plan = project.execution_plans.find(item => item.execution_id === result.execution_id);
    const article = node("article", undefined, "panel result-panel"); article.dataset.controlId = result.control_id;
    article.append(node("p", "RECORDED CONTROL RESULT", "eyebrow"), node("h3", control.control_name), field("Claim challenged", project.claims.find(claim => claim.claim_id === control.claim_tested).statement), field("Status", result.execution_status + " / " + (result.outcome || "No binary interpretation")), field("Interpretation", result.interpretation));
    if (result.effect_estimate) article.append(field(result.effect_estimate.name, String(result.effect_estimate.value)));
    if (result.p_value !== null) article.append(field("Permutation p value", String(result.p_value)));
    if (result.confidence_interval) article.append(field("Confidence interval", result.confidence_interval.lower + " to " + result.confidence_interval.upper + " (requested coverage " + result.confidence_interval.coverage + ")"));
    article.append(field("Warnings", result.warnings.join(" ")), field("Input hashes", result.input_hashes.map(item => item.input_id + ": " + item.sha256).join("; "))); $("result-list").append(article);
    const provenance = node("details"); provenance.append(node("summary", "Execution specification & provenance"), field("Control identifier", result.control_id), field("Execution identifier", result.execution_id), field("Pathway", plan.pathway), field("Scientific assumptions", result.interpretive_metadata.join(" ")), field("Random seed", result.random_seed === null ? "Not recorded" : String(result.random_seed)), field("Fixed runner SHA-256", plan.code_sha256), field("Recorded parameters", plan.parameters.join(" ")), field("Observed software", result.software_versions.map(item => item.name + ": " + item.version).join("; ")));
    if (plan.decision_rule) provenance.append(field("Prespecified decision rule", JSON.stringify(plan.decision_rule)));
    article.append(provenance);
  }
  if (!project.results.length) $("result-list").append(empty("No control has been executed. Download a reproducible package or run a specified numeric control locally."));
  for (const audit of project.audits) {
    const article = node("article", undefined, "panel audit-panel"); article.dataset.assessment = audit.assessment; article.dataset.claimId = audit.claim_id; article.append(field("Claim assessed", project.claims.find(claim => claim.claim_id === audit.claim_id).statement), node("p", audit.assessment.replaceAll("_", " "), "notice"), field("Assessment rationale", audit.rationale));
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
document.querySelectorAll(".tab").forEach(tab => { tab.addEventListener("click", () => switchView(tab.dataset.view)); tab.addEventListener("keydown", event => { const tabs = [...document.querySelectorAll(".tab")], index = tabs.indexOf(tab); let next; if (event.key === "ArrowDown") next = (index + 1) % tabs.length; else if (event.key === "ArrowUp") next = (index + tabs.length - 1) % tabs.length; else if (event.key === "Home") next = 0; else if (event.key === "End") next = tabs.length - 1; else return; event.preventDefault(); switchView(tabs[next].dataset.view, false); tabs[next].focus(); }); });
document.querySelectorAll(".metric-card").forEach(card => card.addEventListener("click", () => switchView(card.dataset.target)));
document.querySelector(".brand").addEventListener("click", event => { event.preventDefault(); switchView("analysis"); });
$("control-search").addEventListener("input", renderControlCards); $("control-class-filter").addEventListener("change", renderControlCards);
$("control-claim-filter").addEventListener("change", renderControlCards);
$("control-state-filter").addEventListener("change", renderControlCards);
$("reset-control-filters").addEventListener("click", () => { $("control-search").value = $("control-class-filter").value = $("control-claim-filter").value = $("control-state-filter").value = ""; renderControlCards(); $("control-search").focus({preventScroll: true}); });
$("open-evidence-library").addEventListener("click", () => { switchView("evidence"); focusDestination($("view-evidence")); });
$("nav-toggle").addEventListener("click", () => { document.body.classList.toggle("nav-open"); syncNavigation(); if (document.body.classList.contains("nav-open")) document.querySelector(".tab.active").focus(); });
$("nav-scrim").addEventListener("click", () => closeNavigation(true));
$("nav-close").addEventListener("click", () => closeNavigation(true));
$("new-workspace").addEventListener("click", () => { if (state.busy || !confirmReplacement()) return; resetWorkspace(); render(); switchView("analysis"); message("Started an empty local workspace. No records are stored automatically."); });
for (const name of ["input", "change"]) document.addEventListener(name, event => { const form = event.target.closest("form"); if (form && event.target.type !== "password") trackForm(form); });
rememberForms();
mobileNavigation.addEventListener("change", () => { if (!mobileNavigation.matches) document.body.classList.remove("nav-open"); syncNavigation(); });
document.addEventListener("keydown", event => { if (event.key === "Escape") { document.querySelectorAll(".workspace-menu[open]").forEach(menu => { menu.open = false; menu.querySelector("summary").focus(); }); if (document.body.classList.contains("nav-open")) { event.preventDefault(); closeNavigation(true); } } });
document.addEventListener("keydown", event => { if (event.key !== "Tab" || !document.body.classList.contains("nav-open")) return; const first = document.querySelector(".brand"), last = document.querySelector(".tab.active"); if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); } else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); } });
document.addEventListener("click", event => { document.querySelectorAll(".workspace-menu[open]").forEach(menu => { if (!menu.contains(event.target)) menu.open = false; }); });
syncNavigation();
$("analysis-form").addEventListener("submit", event => { event.preventDefault(); action(async () => {
  if ((state.project || state.evaluationBundle) && !confirmReplacement()) { message("Kept the current workspace."); return; }
  const form = new FormData(event.target); const value = name => String(form.get(name) || "").trim();
  const context = {}; for (const key of ["organism", "tissue", "data_modality"]) if (value(key)) context[key] = value(key);
  const intake = {question: value("question"), analysis_description: value("analysis_description"), methods: lines(value("methods")), observed_result: value("observed_result"), claim: value("claim"), claim_category: value("claim_category"), computational_support: value("computational_support"), biological_context: context, design: {sampling_unit: value("sampling_unit") || null, data_partition: value("data_partition") || null}, assumptions: lines(value("assumptions"))};
  const data = await api("/api/analyze", {intake}); resetWorkspace(); accept(data, "Local design controls specified. Biological support and applicability remain unvalidated."); switchView("controls");
}); });
function example(kind) {
  if (state.busy || state.drafts.has("analysis-form") && !window.confirm("Replace the unrecorded analysis fields with this hypothetical example?")) return;
  const common = {organism: "Saccharomyces cerevisiae", tissue: "", assumptions: "This is a hypothetical development example, not observed biology.", sampling_unit: "Independent culture", data_partition: "Each culture is an independent unit."};
  const values = kind === "rna" ? {...common, question: "Does a hypothetical treatment change transcript abundance?", claim: "Transcript abundance differs between hypothetical conditions.", analysis_description: "A between-culture differential abundance comparison. The primary analysis was conducted separately.", methods: "Count-based differential abundance comparison", observed_result: "Hypothetical reported abundance differences; no measurements supplied.", claim_category: "COMPARATIVE", computational_support: "COMPARATIVE", data_modality: "bulk transcript counts"} : {...common, organism: "", question: "Can image features distinguish hypothetical cell morphology labels?", claim: "An image-feature classifier predicts morphology labels in new cultures.", analysis_description: "A supervised image-feature classifier evaluated on held-out cultures.", methods: "Image-feature classification", observed_result: "Hypothetical discrimination; no measured score supplied.", claim_category: "PREDICTIVE", computational_support: "PREDICTIVE", data_modality: "microscopy image features", data_partition: "All images from a culture remain in the same data partition."};
  for (const [name, value] of Object.entries(values)) $("analysis-form").elements.namedItem(name).value = value;
  trackForm($("analysis-form")); switchView("analysis"); message("Loaded a hypothetical example. Review the fields, then create the control audit.");
}
$("example-rna").addEventListener("click", () => example("rna")); $("example-ml").addEventListener("click", () => example("ml"));
async function localText(file) { if (!file || file.size > 2 * 1024 * 1024) throw new Error("Choose a local file no larger than 2 MiB."); try { return new TextDecoder("utf-8", {fatal: true, ignoreBOM: true}).decode(await file.arrayBuffer()); } catch { throw new Error("The selected file must contain valid UTF-8 text. Input values are omitted."); } }
async function fileJSON(input) { const file = input.files[0]; if (!file) return null; return (await api("/api/parse-json", {content: await localText(file)})).value; }
$("project-file").addEventListener("change", () => action(async () => { const project = await fileJSON($("project-file")); if (!project) return; const data = await api("/api/analyze", {project}); if (!confirmReplacement()) { $("project-file").value = ""; message("Kept the current workspace."); return; } resetWorkspace(); accept(data, "Opened and audited a local project. Review its evidence receipts before relying on them."); switchView("controls"); }));
$("export-project").addEventListener("click", () => { if (state.project) download(JSON.stringify(state.project, null, 2), "project.controlomics.json"); });
$("export-audit").addEventListener("click", () => download(JSON.stringify(state.audit, null, 2), "network_audit.json"));
$("export-report").addEventListener("click", () => action(async () => { const report = await api("/api/report", {project: requireProject(), network_audit: state.audit}, true); download(report, "controlomics.report.html"); message("Downloaded the local report. Review it before sharing."); }));
$("export-bundle").addEventListener("click", () => action(async () => { const revision = state.revision; const archive = await api("/api/review-bundle", {project: requireProject(), network_audit: state.audit, evaluation_bundle: state.evaluationBundle, annotation_revisions: state.revisions}, true); download(archive, "controlomics.review.zip"); state.preparedRevision = revision; renderSaveState(); message("Prepared a review bundle for download. Retain the file before closing. Unrecorded form edits and raw inputs are omitted."); }));
$("bundle-file").addEventListener("change", () => action(async () => { const file = $("bundle-file").files[0]; if (!file) return; if (file.size > 1024 * 1024) throw new Error("Review archives have a 1 MiB limit."); const bytes = new Uint8Array(await file.arrayBuffer()); let encoded = ""; for (let start = 0; start < bytes.length; start += 16384) encoded += String.fromCharCode(...bytes.subarray(start, start + 16384)); const data = await api("/api/open-bundle", {archive_base64: btoa(encoded)}); const annotations = data.evaluation_bundle ? await api("/api/annotation-template", {bundle: data.evaluation_bundle}) : null; if (!confirmReplacement()) { $("bundle-file").value = ""; message("Kept the current workspace."); return; } resetWorkspace(); state.audit = data.network_audit_restored; state.revisions = data.annotation_revisions; await loadAnnotationBundle(data.evaluation_bundle, false, annotations); accept(data, "Restored validated local records. Hashes and reviewer identities are not authenticated; the ledger may be incomplete."); state.preparedRevision = state.revision; renderSaveState(); switchView("controls"); }));
async function preview(kind, settings) { requireProject(); const result = await api("/api/" + kind + "/preview", settings); state.pending = {kind, settings, hash: result.approve_hash}; $("request-preview").textContent = JSON.stringify(result, null, 2); $("request-dialog").showModal(); $("cancel-request").focus(); message("No external request has been sent. Review the displayed payload."); }
$("literature-form").addEventListener("submit", event => { event.preventDefault(); action(() => preview("literature", {provider: $("literature-provider").value, query: $("literature-query").value.trim(), limit: 5, public_confirmed: $("literature-public").checked})); });
$("model-form").addEventListener("submit", event => { event.preventDefault(); action(async () => preview("model", {endpoint: $("model-endpoint").value.trim(), model: $("model-id").value.trim(), claim_id: $("model-claim").value, fields: (await api("/api/parse-json", {content: $("model-context").value})).value, public_confirmed: $("model-public").checked})); });
$("cancel-request").addEventListener("click", () => { $("request-dialog").close(); state.pending = null; $("model-key").value = ""; message("Request cancelled. No external request was sent."); });
$("request-dialog").addEventListener("cancel", () => { state.pending = null; $("model-key").value = ""; message("Request cancelled. No external request was sent."); });
$("approve-request").addEventListener("click", () => action(async () => { const pending = state.pending; if (!pending) return; $("request-dialog").close(); const body = {...pending.settings, project: requireProject(), approve_hash: pending.hash}; if (pending.kind === "model") { body.api_key = $("model-key").value; $("model-key").value = ""; } state.pending = null; const data = await api("/api/" + pending.kind + (pending.kind === "model" ? "/run" : "/retrieve"), body); accept(data, pending.kind === "model" ? "Received unverified model candidates. External evidence review is required." : "Retrieved publication identities. Statement entailment remains a separate review."); }));
$("review-file").addEventListener("change", () => action(async () => { const review = await fileJSON($("review-file")); if (!review) return; accept(await api("/api/review", {project: requireProject(), review}), "Recorded researcher review with explicit evidence and context states."); $("review-file").value = ""; }));
function executionSettings() {
  requireProject(); const kind = $("execution-kind").value; const assumptions = lines($("execution-assumptions").value);
  if (!assumptions.length) throw new Error("Specify the scientific assumptions before building or running a control.");
  if (!$("execution-control").value) throw new Error($("execution-availability").textContent);
  const config = {kind, assumptions, adapter: $("execution-adapter").value};
  if (kind !== "REFERENCE") { config.random_seed = Number($("execution-seed").value); config.draws = Number($("execution-draws").value); }
  if (kind === "BOOTSTRAP") config.coverage = Number($("execution-coverage").value);
  if (config.adapter === "PAIRED_DIFFERENCE") { config.adapter_rationale = $("adapter-rationale").value.trim(); if (!config.adapter_rationale) throw new Error("Explain why the paired adapter applies to this specification."); }
  if (kind === "REFERENCE") { if (!$("execution-expected").value.trim()) throw new Error("Specify the independently expected difference before execution."); config.expected_difference = Number($("execution-expected").value); config.absolute_tolerance = Number($("execution-tolerance").value); }
  return {project: state.project, control_id: $("execution-control").value, config};
}
function updateExecutionAvailability() {
  const project = state.project, paired = $("execution-adapter").value === "PAIRED_DIFFERENCE";
  const available = [...$("execution-control").options].filter(option => option.value);
  const selected = Boolean($("execution-control").value && available.some(option => option.value === $("execution-control").value));
  $("run-control").disabled = !selected || !$("numeric-file").files.length;
  $("download-package").disabled = !selected;
  $("execution-open-controls").disabled = !project;
  $("execution-open-paired").disabled = !project;
  $("execution-open-paired").hidden = !paired || available.length > 0;
  const reviewed = project?.controls.filter(item => (paired ? item.scientific_level === "STATISTICAL" && item.control_class === "NULL" && item.method_basis === pairedBasis : item.scientific_level === "TECHNICAL" && ["POSITIVE", "NEGATIVE"].includes(item.control_class)) && ["METHOD_BASED", "EVIDENCE_BACKED"].includes(item.evidence_status)) || [];
  $("execution-availability").textContent = !project ? "Create or open a project to select an executable specification. Local CSV inspection remains available." : !available.length ? reviewed.length ? "All compatible reviewed controls in this snapshot already have execution plans. Import their results or retain a separate original snapshot for another run." : paired ? "No reviewed complete-pair specification is available. State its claim, applicability, and assumptions in the paired specification form; other controls require their own adapters." : "No reviewed independent-group technical reference is available. Inspect the controls and method review. Biological, design, and other statistical specifications require applicable adapters." : !selected ? "Select a reviewed control explicitly. " + available.length + " compatible specification" + (available.length === 1 ? " is" : "s are") + " available. Existing procedure inputs are retained; check them for your selected control." : $("numeric-file").files.length ? "The selected control can be run locally or exported as a package. Review the input, expected behavior, and assumptions before execution." : "The selected control can be exported as a package. Choose a local CSV to inspect or run it on this computer.";
}
$("execution-control").addEventListener("change", updateExecutionAvailability);
$("execution-open-controls").addEventListener("click", () => { switchView("controls"); focusDestination($("view-controls")); });
$("execution-open-paired").addEventListener("click", () => { const panel = $("paired-form").closest("details"); panel.open = true; panel.scrollIntoView({block: "start", behavior: "instant"}); focusDestination(panel.querySelector("summary")); });
function syncExecutionFields() {
  const paired = $("execution-adapter").value === "PAIRED_DIFFERENCE";
  $("execution-kind").options[0].disabled = paired;
  if (paired && $("execution-kind").value === "REFERENCE") $("execution-kind").value = "PERMUTATION";
  const reference = $("execution-kind").value === "REFERENCE", bootstrap = $("execution-kind").value === "BOOTSTRAP";
  $("adapter-rationale-label").hidden = !paired; $("adapter-rationale").required = paired;
  $("execution-reference-fields").hidden = !reference; $("execution-resampling-fields").hidden = reference;
  for (const id of ["execution-expected", "execution-tolerance"]) { $(id).disabled = !reference; $(id).required = reference; }
  for (const id of ["execution-seed", "execution-draws"]) $(id).disabled = reference;
  $("execution-coverage-label").hidden = !bootstrap; $("execution-coverage").disabled = !bootstrap;
  $("csv-layout").textContent = paired ? "CSV columns: pair,condition,value. Exactly one value for condition 0 and 1 per pair, 2 to 1,000 complete pairs. Pair identifiers do not establish independence across pairs." : "CSV columns: unit,label,value. Unique unit IDs without outer whitespace, labels 0 or 1, at least two units per group, maximum 2,000 rows. UTF-8 with an optional byte-order mark is accepted.";
}
function clearInputSummary() { state.inputSummary = null; $("input-summary").hidden = true; $("input-summary").replaceChildren(); $("export-input-summary").disabled = true; $("inspect-input").disabled = !$("numeric-file").files.length; updateExecutionAvailability(); }
$("numeric-file").addEventListener("change", clearInputSummary);
$("execution-kind").addEventListener("change", syncExecutionFields);
$("inspect-input").addEventListener("click", () => action(async () => {
  const data = await api("/api/inspect-input", {adapter: $("execution-adapter").value, csv: await localText($("numeric-file").files[0])});
  state.inputSummary = data.input_summary; const summary = state.inputSummary, panel = $("input-summary");
  panel.replaceChildren(node("h3", "Local input inspection"));
  const dimensions = node("div", undefined, "input-dimensions"); dimensions.append(field("Data rows", String(summary.rows)));
  if (summary.complete_pairs !== null) dimensions.append(field("Complete pairs", String(summary.complete_pairs)));
  else dimensions.append(field("Group 0 units", String(summary.group_zero_units)), field("Group 1 units", String(summary.group_one_units)));
  dimensions.append(field("Input bytes", String(summary.input_bytes))); panel.append(dimensions, field("Exact input SHA-256", summary.input_sha256), node("p", "Columns and finite values checked. No control has been executed. Sampling assumptions still require justification.", "muted"));
  panel.hidden = false; $("export-input-summary").disabled = false; message("Inspected the selected local CSV. The summary omits raw values and identifiers.");
}));
$("export-input-summary").addEventListener("click", () => { if (state.inputSummary) download(JSON.stringify(state.inputSummary, null, 2), "controlomics.input-summary.json"); });
syncExecutionFields();
$("execution-form").addEventListener("submit", event => { event.preventDefault(); action(async () => { const settings = executionSettings(); settings.csv = await localText($("numeric-file").files[0]); accept(await api("/api/execute", settings), "Recorded the local control result and conservative scientific audit."); clearDraft("execution-form"); switchView("audit"); }); });
$("download-package").addEventListener("click", () => action(async () => { const data = await api("/api/package", executionSettings()); const bytes = Uint8Array.from(atob(data.package_base64), character => character.charCodeAt(0)); download(new Blob([bytes], {type: "application/zip"}), data.filename); accept(data, "Downloaded a reproducible execution package. The saved package includes its planned project snapshot."); }));
$("result-file").addEventListener("change", () => action(async () => { const result = await fileJSON($("result-file")); if (!result) return; accept(await api("/api/import-results", {project: requireProject(), result}), "Imported and checked the result against its execution plan."); $("result-file").value = ""; }));
const categories = ["DESCRIPTIVE", "ASSOCIATIONAL", "COMPARATIVE", "PREDICTIVE", "STATISTICAL", "FUNCTIONAL", "MECHANISTIC", "CAUSAL"];
for (const id of ["new-claim-category", "new-claim-support"]) options($(id), [["", "Choose a category"], ...categories.map(category => [category, category])]);
$("narrative-form").addEventListener("submit", event => { event.preventDefault(); action(async () => { const data = await api("/api/interpret", {description: $("narrative-description").value}); state.narrative = data.draft; $("narrative-preview").textContent = JSON.stringify(data.draft, null, 2); $("narrative-result").hidden = false; message("Drafted local fields. Review them and explicitly choose the claim and support categories."); }); });
$("use-narrative").addEventListener("click", () => { if (state.busy || !state.narrative || state.drafts.has("analysis-form") && !window.confirm("Apply this description draft over the unrecorded analysis fields?")) return; const form = $("analysis-form"); for (const [name, value] of Object.entries(state.narrative.fields)) { const element = form.elements.namedItem(name); if (element) element.value = value; } for (const name of ["claim_category", "computational_support"]) if (!state.narrative.fields[name]) form.elements.namedItem(name).value = ""; trackForm(form); message("Applied provisional fields. Complete missing values and review every field before creating a project."); });
$("claim-form").addEventListener("submit", event => { event.preventDefault(); action(async () => { const form = new FormData(event.target); const claim = {statement: form.get("statement"), category: form.get("category"), computational_support: form.get("computational_support"), assumptions: lines(String(form.get("assumptions") || ""))}; accept(await api("/api/add-claim", {project: requireProject(), claim}), "Added an explicit claim with its own design controls."); event.target.reset(); clearDraft("claim-form"); switchView("controls"); }); });
function editCandidate(control = null) {
  if (state.busy || state.drafts.has("candidate-form") && !window.confirm("Discard the unrecorded candidate specification inputs and open this specification?")) { message("Kept the current candidate inputs."); return; }
  const form = $("candidate-form"); form.reset();
  if (control) { const values = {control_id: control.control_id, claim_id: control.claim_tested, name: control.control_name, control_class: control.control_class, scientific_level: control.scientific_level, rationale: control.scientific_rationale, expected_behavior: control.expected_behavior, failure_interpretation: control.failure_interpretation, method_basis: control.method_basis || "", priority: control.priority, priority_rationale: control.priority_rationale, uncertainties: control.uncertainties.join("\n"), limitations: control.limitations.join("\n")}; for (const [name, value] of Object.entries(values)) form.elements.namedItem(name).value = value; $("candidate-evidence").checked = control.evidence_required; }
  clearDraft("candidate-form"); $("candidate-panel").open = true; $("candidate-panel").scrollIntoView({block: "start"}); focusDestination($("candidate-panel").querySelector("summary"));
}
$("add-control").addEventListener("click", () => { requireProject(); editCandidate(); });
$("candidate-level").addEventListener("change", () => { if (["BIOLOGICAL", "MECHANISTIC"].includes($("candidate-level").value)) $("candidate-evidence").checked = true; });
$("candidate-form").addEventListener("submit", event => { event.preventDefault(); action(async () => { const form = new FormData(event.target); const value = name => String(form.get(name) || "").trim(); const control = {}; for (const name of ["name", "control_class", "scientific_level", "rationale", "expected_behavior", "failure_interpretation", "priority", "priority_rationale"]) control[name] = value(name); control.evidence_required = $("candidate-evidence").checked; control.method_basis = value("method_basis") || null; control.uncertainties = lines(value("uncertainties")); control.limitations = lines(value("limitations")); const specification = {claim_id: value("claim_id"), control, control_id: value("control_id") || null}; accept(await api("/api/specify-control", {project: requireProject(), specification}), "Saved an unverified researcher specification. Complete evidence review before relying on it."); $("candidate-panel").open = false; clearDraft("candidate-form"); }); });
$("check-methods").addEventListener("click", () => action(async () => accept(await api("/api/method-review", {project: requireProject()}), "Reviewed technical and statistical specifications with method bases. This does not establish empirical validity.")));
async function openReview(controlId) {
  const previous = state.reviewTemplate?.control_id;
  if (state.drafts.has("human-review-form") && !window.confirm("Discard the unrecorded source-review inputs and open this control? Full supplied source text is excluded from exports.")) { if (previous) $("review-control").value = previous; message("Kept the unrecorded source-review inputs."); return; }
  let data; try { data = await api("/api/review-template", {project: requireProject(), control_id: controlId}); } catch (error) { if (previous) $("review-control").value = previous; throw error; }
  switchView("evidence"); $("review-control").value = controlId; state.reviewTemplate = data.template; clearDraft("human-review-form");
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
  $("review-panel").open = true; $("review-panel").scrollIntoView({block: "start"}); focusDestination($("review-panel").querySelector("summary")); message("Review the exact statements against source text. No review has been recorded yet.");
}
$("review-control").addEventListener("change", () => action(() => openReview($("review-control").value)));
$("human-review-form").addEventListener("submit", event => { event.preventDefault(); action(async () => {
  const template = state.reviewTemplate; if (!template || template.control_id !== $("review-control").value) throw new Error("Open the selected control's review first.");
  if (!$("human-attestation").checked) throw new Error("A real researcher must attest this source review.");
  if (template.supersedes_review_sha256 && !$("supersede-review").checked) throw new Error("Explicitly approve replacement of the prior review or keep the previous record.");
  const statements = []; for (const [index, statement] of template.statements.entries()) { const value = suffix => $("statement-" + index + "-" + suffix).value.trim(); statements.push({evidence_id: value("evidence"), statement, relationship: value("relationship"), source_text: value("source"), excerpt: value("excerpt"), locator: value("locator"), rationale: value("rationale"), source_context: (await api("/api/parse-json", {content: value("context")})).value}); }
  const review = {control_id: template.control_id, reviewer: $("review-researcher").value.trim(), statements, limitations: lines($("review-limitations").value), supersedes_review_sha256: template.supersedes_review_sha256};
  accept(await api("/api/review", {project: requireProject(), review}), "Recorded a researcher attestation with explicit evidence and context outcomes."); clearDraft("human-review-form"); state.reviewTemplate = null; $("statement-reviews").replaceChildren(); $("human-attestation").checked = false; $("review-panel").open = false; switchView("controls");
}); });
$("evaluation-form").addEventListener("submit", event => { event.preventDefault(); action(async () => {
  if ($("evaluation-file").files[0] && !await loadAnnotationBundle(await fileJSON($("evaluation-file")))) return;
  if (!state.evaluationBundle) throw new Error("Choose a local evaluation bundle first.");
  const data = await api("/api/evaluate", {bundle: state.evaluationBundle, partition: $("evaluation-partition").value || null}); state.evaluation = data.evaluation;
  const report = data.evaluation, container = $("evaluation-result"); container.replaceChildren();
  const overview = node("article", undefined, "panel"); overview.append(node("h3", report.dataset_id), field("Provider and partition", report.provider + " / " + report.partition), field("Recorded bundle SHA-256", report.bundle_sha256), node("p", "Metrics use the recorded bundle. Unrecorded judgment edits are excluded.", "muted"), field("Annotation origins", "References: " + report.reference_origin + "; judgments: " + report.judgment_origin), field("Coverage", report.coverage.cases + " cases, " + report.coverage.recommendations + " recommendations, " + report.coverage.appropriateness_assessed + " assessed for appropriateness, " + report.coverage.uncertain_or_missing_appropriateness + " uncertain or missing.")); container.append(overview);
  const panel = node("div", undefined, "panel metric-panel"), table = node("table"), head = node("thead"), header = node("tr"); for (const label of ["Metric", "Result", "Denominator", "Definition"]) header.append(node("th", label)); head.append(header); table.append(head);
  const body = node("tbody"); for (const [name, metric] of Object.entries(report.metrics)) { const row = node("tr"); row.append(node("td", name.replaceAll("_", " ")), node("td", metric.value === null ? "Unavailable" : String(Number(metric.value.toFixed(4)))), node("td", String(metric.denominator)), node("td", metric.definition)); [...row.children].forEach((cell, index) => { cell.dataset.label = ["Metric", "Result", "Denominator", "Definition"][index]; }); body.append(row); } table.append(body); panel.append(table); container.append(panel);
  const limits = node("article", undefined, "panel"); limits.append(field("Limitations", report.limitations.join(" ")), field("Interval interpretation", "The exported JSON includes descriptive Wilson intervals. Correlated cases and controls require a separate inferential design.")); container.append(limits);
  $("export-evaluation").disabled = false; clearDraft("evaluation-form"); message("Calculated local metrics with explicit denominators. Unassessed scientific quality remains unavailable.");
}); });
$("export-evaluation").addEventListener("click", () => { if (state.evaluation) download(JSON.stringify(state.evaluation, null, 2), "controlomics.evaluation.json"); });
function invalidateEvaluation(notice = "The evaluation input changed. Calculate this recorded snapshot to see its metrics.") { state.evaluation = null; $("evaluation-result").replaceChildren(empty(notice)); $("export-evaluation").disabled = true; }
$("evaluation-partition").addEventListener("change", () => invalidateEvaluation("The selected partition changed. Calculate metrics for this selection."));
$("execution-adapter").addEventListener("change", () => { syncExecutionFields(); clearInputSummary(); render(); });
$("paired-form").addEventListener("submit", event => { event.preventDefault(); action(async () => { accept(await api("/api/specify-paired", {project: requireProject(), claim_id: $("paired-claim").value, rationale: $("paired-rationale").value.trim(), assumptions: lines($("paired-assumptions").value)}), "Specified a paired statistical control. Researcher-supplied assumptions still need justification."); $("execution-adapter").value = "PAIRED_DIFFERENCE"; $("execution-adapter").dispatchEvent(new Event("change")); clearDraft("paired-form"); }); });
async function loadAnnotationBundle(bundle, resetRevisions = true, prepared = undefined) {
  const data = prepared !== undefined ? prepared : bundle ? await api("/api/annotation-template", {bundle}) : null;
  if (resetRevisions && state.drafts.has("annotation-form") && !window.confirm("Replace the loaded evaluation and its unrecorded judgment edits? Record and export judgments first if you need to retain them.")) { message("Kept the current evaluation and judgment edits."); return false; }
  invalidateEvaluation();
  state.evaluationBundle = data?.bundle || null; state.annotationHash = data?.bundle_sha256 || null;
  state.annotationDraft = data ? structuredClone(data.bundle) : null; state.annotationCase = null;
  if (resetRevisions) state.revisions = [];
  clearDraft("annotation-form"); clearDraft("evaluation-form"); if (data) recordChange();
  $("annotation-panel").hidden = !data; $("export-evaluation-bundle").disabled = !data; $("export-revisions").disabled = !data;
  $("annotation-attestation").checked = false; $("annotation-reviewer").value = ""; $("annotation-origin").value = ""; $("evaluation-file").value = "";
  if (!data) return true;
  for (const prediction of state.annotationDraft.predictions.cases) for (const control of prediction.controls) {
    if (!state.annotationDraft.judgments.some(item => item.case_id === prediction.case_id && item.control_id === control.control_id)) state.annotationDraft.judgments.push({case_id: prediction.case_id, control_id: control.control_id, appropriate: null, unsupported: null, matched_reference_ids: [], rationale: "No judgment recorded."});
  }
  options($("annotation-case"), data.bundle.dataset.cases.map(item => [item.case_id, item.case_id + ": " + item.description]));
  renderAnnotationCase();
  return true;
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
$("open-annotations").addEventListener("click", () => action(async () => { if ($("evaluation-file").files[0] && !await loadAnnotationBundle(await fileJSON($("evaluation-file")))) return; if (!state.evaluationBundle) throw new Error("Choose a local evaluation bundle first."); $("annotation-panel").open = true; $("annotation-panel").scrollIntoView({block: "start"}); focusDestination($("annotation-panel").querySelector("summary")); message("Opened imported recommendations and reference definitions. No new judgments have been recorded."); }));
$("annotation-form").addEventListener("submit", event => { event.preventDefault(); action(async () => { saveAnnotationCase(); if (!$("annotation-attestation").checked) throw new Error("A real reviewer must attest the judgments."); const submission = {bundle_sha256: state.annotationHash, judgment_origin: $("annotation-origin").value, annotator: $("annotation-reviewer").value.trim(), human_attested: true, judgments: state.annotationDraft.judgments, evidence_decisions: state.annotationDraft.evidence_decisions}; const data = await api("/api/annotate", {bundle: state.evaluationBundle, submission}); state.revisions.push(data.revision); await loadAnnotationBundle(data.bundle, false); state.evaluation = null; $("evaluation-result").replaceChildren(empty("Judgments changed. Calculate the current snapshot to see updated metrics.")); $("export-evaluation").disabled = true; message("Recorded supplied judgments and snapshot hashes. Export this bundle and revisions; identities remain unauthenticated."); }); });
$("export-evaluation-bundle").addEventListener("click", () => { if (state.evaluationBundle) download(JSON.stringify(state.evaluationBundle, null, 2), "controlomics.annotations.json"); });
$("export-revisions").addEventListener("click", () => download(JSON.stringify(state.revisions, null, 2), "controlomics.annotation_revisions.json"));
window.addEventListener("beforeunload", event => { if (hasUnsavedWork()) { event.preventDefault(); event.returnValue = ""; } });
refreshSession().then(() => {
  render();
  if (location.hash === "#demo=transcriptomics" || location.hash === "#demo=microscopy") {
    example(location.hash.endsWith("microscopy") ? "ml" : "rna");
    $("analysis-form").requestSubmit();
  }
}).catch(() => message("Local session could not be initialized. Keep any existing workspace open and retain exports before reloading.", true));
