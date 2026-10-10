"""Self-contained, escaped scientific reports without remote assets or scripts."""

import html
import json
from pathlib import Path
from urllib.parse import quote
from controlomics import __version__
from controlomics.reasoning import describe_design


def esc(value):
    return html.escape(str(value), quote=True)


def citation_url(identifier):
    if identifier.namespace == "DOI":
        return "https://doi.org/" + quote(identifier.value, safe="/")
    if identifier.namespace == "PMID":
        return "https://pubmed.ncbi.nlm.nih.gov/" + quote(identifier.value) + "/"
    if identifier.namespace == "PMCID":
        return "https://pmc.ncbi.nlm.nih.gov/articles/" + quote(identifier.value) + "/"
    return None


def render_report(project, network_audit=()):
    from controlomics.artifacts import validated_ledger
    from controlomics.privacy import canonical_json
    from controlomics.project import parse_project_json
    project = parse_project_json(canonical_json(project.model_dump(mode="json")))
    network_audit = validated_ledger(network_audit)
    controls = project.controls + project.candidates
    claims = {claim.claim_id: claim for claim in project.claims}
    control_map = {control.control_id: control for control in controls}
    plans = {plan.execution_id: plan for plan in project.execution_plans}
    blocks = []
    def paragraph(label, text):
        return f"<p><strong>{esc(label)}:</strong> {esc(text)}</p>"
    def reference(kind, identifier, label):
        return f"<a href='#{esc(kind + '-' + identifier)}'>{esc(label)}</a>"
    blocks.append("<header class='report-header'><p class='eyebrow'>LOCAL SCIENTIFIC REVIEW</p><h1>Controlomics scientific audit</h1>" +
        f"<p class='report-question'>{esc(project.analysis.scientific_question)}</p></header>" +
        "<p class='notice'>Research alpha. Scientific validity and cross-domain generalization have not been demonstrated. Imported records and reviewer identities are not authenticated.</p>")
    counts = (("Scientific claims", len(project.claims)), ("Control specifications", len(controls)),
        ("Publication records", len(project.evidence)), ("Completed executions", sum(result.execution_status == "COMPLETED" for result in project.results)))
    blocks.append("<div class='report-metrics' aria-label='Recorded project counts'>" + "".join(
        f"<div><span>{esc(label)}</span><strong>{value}</strong></div>" for label, value in counts) + "</div>" +
        "<p class='muted'>Record counts describe this project. Publication identity, statement support, completed execution, and scientific validity are separate.</p>")
    sections = (("analysis", "Analysis and claims"), ("controls", "Controls"), ("evidence", "Publication identities"),
        ("execution", "Execution results"), ("assessment", "Assessment"), ("network", "Network audit"), ("provenance", "Provenance"))
    blocks.append("<nav class='report-nav' aria-label='Report sections'>" + "".join(
        f"<a href='#{identifier}'>{label}</a>" for identifier, label in sections) + "</nav>")
    blocks.append(paragraph("Project identifier", project.manifest.project_id) + paragraph("Created", project.manifest.created_at.isoformat()) +
        paragraph("Project version", project.manifest.controlomics_version))
    blocks.append(paragraph("Privacy", project.privacy.classification + "; project and raw inputs remain local"))
    blocks.append("<h2 id='analysis'>Analysis and claim</h2>" + paragraph("Question", project.analysis.scientific_question) +
                  paragraph("Analysis", project.analysis.analysis_description) + paragraph("Reported result", project.analysis.observed_result))
    blocks.append(paragraph("Methods", "; ".join(project.analysis.methods)) +
        paragraph("Sampling unit", project.analysis.design.sampling_unit or "Unspecified") +
        paragraph("Independence assumptions", "; ".join(project.analysis.design.independence_assumptions) or "Not supplied"))
    for dimension, value in project.analysis.biological_context.model_dump().items():
        if dimension != "schema_version" and value:
            blocks.append(paragraph("Context: " + dimension.replace("_", " "), "; ".join(value) if isinstance(value, tuple) else value))
    for claim in project.claims:
        blocks.append(f"<article class='claim-record' id='{esc('claim-' + claim.claim_id)}'>" +
            paragraph("Claim identifier", claim.claim_id) + paragraph("Claim", claim.statement) +
            paragraph("Category and support", claim.category + "; " + claim.computational_support) +
            paragraph("Claim assumptions", "; ".join(claim.assumptions) or "Not supplied"))
        profile = describe_design(project.analysis, claim)
        blocks.append(paragraph("Provisional design cues", "; ".join(cue.facet + ": " + cue.basis for cue in profile.cues) or "No analytical operation recognized."))
        blocks.append(paragraph("Reasoning limits", "; ".join(profile.limitations)))
        for warning in claim.interpretation_warnings:
            blocks.append(paragraph("Interpretation warning", warning))
        blocks.append("</article>")
    blocks.append("<h2 id='controls'>Control recommendations</h2>")
    if not controls:
        blocks.append("<p class='empty'>No control specification is recorded. Inspect the stated analysis and retained uncertainty.</p>")
    for control in controls:
        content = f"<article id='{esc('control-' + control.control_id)}'><h3>" + esc(control.control_name) + "</h3>"
        content += "<p class='claim-reference'><strong>Claim challenged:</strong> " + reference("claim", control.claim_tested, claims[control.claim_tested].statement) + "</p>"
        for label, value in (("Control ID", control.control_id), ("Class and level", control.control_class + "; " + control.scientific_level),
            ("Claim tested", control.claim_tested), ("Evidence state", control.evidence_status),
            ("Rationale", control.scientific_rationale), ("Expected behavior", control.expected_behavior),
            ("Failure interpretation", control.failure_interpretation), ("Context", control.context_compatibility.status),
            ("Priority", control.priority + ": " + control.priority_rationale), ("Execution", control.execution_status)):
            content += paragraph(label, value)
        content += paragraph("Required inputs", "; ".join(item.description for item in control.required_inputs) or "Must be specified before execution.")
        if control.method_basis:
            content += paragraph("Method basis", control.method_basis)
        content += paragraph("Uncertainty", "; ".join(control.uncertainties) or "No uncertainty notes supplied; this does not establish certainty.")
        content += paragraph("Limitations", "; ".join(control.limitations))
        for link in control.supporting_evidence:
            content += "<p>" + reference("evidence", link.evidence_id, "Inspect linked publication " + link.evidence_id) + "</p>"
            content += paragraph("Evidence link", link.evidence_id + ": " + link.relationship + "; " + link.rationale)
            content += paragraph("Exact reviewed statement", link.statement) + paragraph("Source locator", link.locator or "Not supplied")
        for comparison in control.context_compatibility.comparisons:
            content += paragraph("Context comparison", comparison.dimension + ": " + comparison.status + "; " + comparison.rationale)
        blocks.append(content + "</article>")
    blocks.append("<h2 id='evidence'>Retrieved publication identities</h2><p>Publication existence is distinct from statement entailment. Abstracts and full text are omitted.</p>")
    if not project.evidence:
        blocks.append("<p class='empty'>No publication identity is recorded in this project.</p>")
    for item in project.evidence:
        content = f"<article id='{esc('evidence-' + item.evidence_id)}'><h3>" + esc(item.title or "Title unavailable") + "</h3>" + paragraph("Source", item.source)
        content += paragraph("Authors and year", "; ".join(item.authors) + "; " + str(item.year or "unknown"))
        for identifier in item.identifiers:
            url = citation_url(identifier)
            label = identifier.namespace + ": " + identifier.value
            content += f"<p><a rel='noopener noreferrer' href='{esc(url)}'>{esc(label)}</a></p>" if url else paragraph("Identifier", label)
        content += paragraph("Identity status", item.existence_status) + paragraph("Limitations", "; ".join(item.limitations))
        content += paragraph("Licensing", item.licensing_restrictions or "Not determined")
        blocks.append(content + "</article>")
    blocks.append("<h2 id='execution'>Execution results</h2>")
    if not project.results:
        blocks.append("<p class='empty'>No control result is recorded. Specifications and planned packages are not completed executions.</p>")
    for result in project.results:
        plan = plans[result.execution_id]
        blocks.append(f"<article id='{esc('result-' + result.result_id)}'><h3>{esc(control_map[result.control_id].control_name)}</h3><p>" +
            reference("control", result.control_id, "Inspect the tested control specification") + "</p>" +
            paragraph("Execution identifier and pathway", result.execution_id + "; " + plan.pathway) +
            paragraph("Recorded parameters", "; ".join(plan.parameters) or "Not supplied") +
            paragraph("Fixed runner SHA-256", plan.code_sha256 or "Not recorded"))
        if plan.decision_rule:
            blocks.append(paragraph("Prespecified decision rule", json.dumps(plan.decision_rule.model_dump(mode="json"), sort_keys=True)))
        blocks.append(paragraph("Result", result.result_id + "; " + result.execution_status + "; " + (result.outcome or "No binary interpretation")))
        if result.effect_estimate:
            blocks.append(paragraph(result.effect_estimate.name, result.effect_estimate.value))
        if result.p_value is not None:
            blocks.append(paragraph("Permutation p value", result.p_value))
        if result.confidence_interval:
            interval = result.confidence_interval
            blocks.append(paragraph("Confidence interval", f"{interval.lower} to {interval.upper}; requested coverage {interval.coverage}; {interval.method}"))
        if result.null_distribution_summary:
            null = result.null_distribution_summary
            blocks.append(paragraph("Null distribution", f"{null.draws} assignments; mean {null.mean}; standard deviation {null.standard_deviation}; {null.null_hypothesis}"))
        blocks.append(paragraph("Scientific assumptions", "; ".join(result.interpretive_metadata)) +
            paragraph("Warnings", "; ".join(result.warnings)) + paragraph("Random seed", result.random_seed) +
            paragraph("Input hashes", "; ".join(item.input_id + ": " + item.sha256 for item in result.input_hashes)) +
            paragraph("Observed software", "; ".join(item.name + ": " + item.version for item in result.software_versions)))
        blocks.append(paragraph("Interpretation", result.interpretation or "No interpretation supplied."))
        if result.errors:
            blocks.append(paragraph("Recorded errors", "; ".join(result.errors)))
        blocks.append("</article>")
    blocks.append("<h2 id='assessment'>Adversarial assessment</h2>")
    if not project.audits:
        blocks.append("<p class='empty'>No assessment is recorded in this snapshot.</p>")
    for audit in project.audits:
        blocks.append("<article><p class='claim-reference'><strong>Claim assessed:</strong> " + reference("claim", audit.claim_id, claims[audit.claim_id].statement) + "</p>")
        blocks.append(paragraph("Assessment", audit.assessment) + paragraph("Rationale", audit.rationale) +
                      paragraph("Uncertainties", "; ".join(audit.uncertainties)) + paragraph("Limitations", "; ".join(audit.limitations)))
        for identifier in audit.result_ids:
            blocks.append("<p>" + reference("result", identifier, "Referenced result " + identifier) + "</p>")
        blocks.append("</article>")
    blocks.append("<h2 id='network'>Network audit</h2><p class='muted'>The supplied ledger records declared events. An empty ledger does not prove that no other transmission occurred.</p>")
    if not network_audit:
        blocks.append("<p>No external requests were recorded in this run.</p>")
    for event in network_audit:
        blocks.append(paragraph("Destination and purpose", event["url"] + "; " + event["purpose"]) +
                      paragraph("Request", event["request_sha256"] + "; " + event["status"]))
        blocks.append(paragraph("Time and transmission", event.get("sent_at", "Unknown") + "; " + event.get("payload_transmission", "Unknown")))
        for field in event["fields"]:
            blocks.append(paragraph("Approved outbound field", field["name"] + ": " + field["value"] + " (" + field["classification"] + ")"))
    blocks.append("<h2 id='provenance'>Provenance</h2>")
    for event in project.provenance:
        blocks.append(paragraph(event.action, event.recorded_at.isoformat() + "; " + ", ".join(event.record_ids) + "; Controlomics " + event.controlomics_version))
        if event.model:
            blocks.append(paragraph("Proposal provider", event.model.provider + "; " + event.model.model_identifier + "; policy hash " + event.model.prompt_template_sha256))
        if event.warnings:
            blocks.append(paragraph("Provenance warnings", "; ".join(event.warnings)))
        if event.input_hashes:
            blocks.append(paragraph("Provenance input hashes", "; ".join(item.input_id + ": " + item.sha256 for item in event.input_hashes)))
    blocks.append(f"<footer>Controlomics. Rendered with {esc(__version__)}. Retain the corresponding project and execution artifacts for reproducibility.</footer>")
    css = """
*{box-sizing:border-box}body{max-width:1050px;margin:46px auto;padding:0 28px;background:#f5f7f8;color:#182d3d;font:14px/1.75 'Segoe UI',system-ui,sans-serif}
.report-header{padding:0 0 18px;border-bottom:1px solid #dce5e7}.eyebrow{font-size:10px;letter-spacing:.16em;color:#627480;margin:0 0 12px}
h1{font:400 34px/1.25 Georgia,serif;letter-spacing:-.025em;margin:0 0 14px}.report-question{color:#526977;font-size:16px;margin:0;max-width:900px}
h2{font-size:22px;line-height:1.35;margin:40px 0 16px;letter-spacing:-.02em;scroll-margin-top:20px}h3{font-size:17px;line-height:1.45;margin:0 0 17px}
article{background:#fff;border:1px solid #dce5e7;padding:25px;margin:18px 0;border-radius:10px}.claim-record{border-left:3px solid #8fb8ac}
p{overflow-wrap:anywhere;margin:12px 0}p>strong{font-weight:600}a{color:#176157;text-underline-offset:3px}.claim-reference{background:#f2f7f5;padding:12px 14px;border-radius:6px}
.notice{padding:16px 19px;background:#faf6ed;border:1px solid #e7deca;border-left:3px solid #bca777;border-radius:6px;color:#806b41;font-size:12px;margin:25px 0}
.report-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:22px 0 10px}.report-metrics>div{background:#fff;border:1px solid #dce5e7;padding:14px 17px;border-radius:8px}
.report-metrics span{display:block;color:#627480;font-size:11px}.report-metrics strong{display:block;font-size:27px;font-weight:500;line-height:1.6;font-variant-numeric:tabular-nums}
.muted{font-size:11px;color:#627480}.report-nav{display:flex;gap:9px;flex-wrap:wrap;padding:14px 0 22px;border-bottom:1px solid #dce5e7;margin:20px 0}
.report-nav a{font-size:11px;text-decoration:none;border:1px solid #d1dfdb;padding:5px 10px;border-radius:5px;background:#fff}
.empty{padding:20px;border:1px dashed #cddde1;background:#fafcfc;border-radius:7px;color:#627480;font-size:12px}footer{margin:40px 0 25px;padding-top:20px;border-top:1px solid #dce5e7;color:#627480;font-size:11px}
@media(max-width:600px){body{padding:0 18px;margin:25px auto}h1{font-size:28px}.report-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}article{padding:20px}}
@media print{@page{size:auto;margin:17mm}body{max-width:none;margin:0;padding:0;background:white;color:#111;font-size:10pt}.report-nav{display:none}h1{font-size:22pt}h2{font-size:15pt;break-after:avoid}h3{break-after:avoid}article{border-radius:0;padding:14px;box-shadow:none}p{orphans:3;widows:3}.report-metrics>div{break-inside:avoid}.notice,.claim-reference{background:white;color:#111}a{color:#111}footer{font-size:8pt}}
"""
    return "<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'\"><title>Controlomics scientific audit</title><style>" + css + "</style></head><body>" + "".join(blocks) + "</body></html>"


def write_report(project, path: Path, network_audit=()):
    from controlomics.storage import write_text_atomic
    write_text_atomic(path, render_report(project, network_audit))
