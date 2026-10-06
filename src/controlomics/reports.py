"""Self-contained, escaped scientific reports without remote assets or scripts."""

import html
from pathlib import Path
from urllib.parse import quote


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
    blocks = []
    def paragraph(label, text):
        return f"<p><strong>{esc(label)}:</strong> {esc(text)}</p>"
    blocks.append("<h1>Controlomics scientific audit</h1><p class='notice'>Research alpha. Scientific validity and cross-domain generalization have not been demonstrated.</p>")
    blocks.append(paragraph("Privacy", project.privacy.classification + "; project and raw inputs remain local"))
    blocks.append("<h2>Analysis and claim</h2>" + paragraph("Question", project.analysis.scientific_question) +
                  paragraph("Analysis", project.analysis.analysis_description) + paragraph("Reported result", project.analysis.observed_result))
    blocks.append(paragraph("Methods", "; ".join(project.analysis.methods)) +
        paragraph("Sampling unit", project.analysis.design.sampling_unit or "Unspecified") +
        paragraph("Independence assumptions", "; ".join(project.analysis.design.independence_assumptions) or "Not supplied"))
    for dimension, value in project.analysis.biological_context.model_dump().items():
        if dimension != "schema_version" and value:
            blocks.append(paragraph("Context: " + dimension.replace("_", " "), "; ".join(value) if isinstance(value, tuple) else value))
    for claim in project.claims:
        blocks.append(paragraph("Claim", claim.statement) + paragraph("Category and support", claim.category + "; " + claim.computational_support))
        for warning in claim.interpretation_warnings:
            blocks.append(paragraph("Interpretation warning", warning))
    blocks.append("<h2>Control recommendations</h2>")
    for control in project.candidates + project.controls:
        content = "<article><h3>" + esc(control.control_name) + "</h3>"
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
            content += paragraph("Evidence link", link.evidence_id + ": " + link.relationship + "; " + link.rationale)
            content += paragraph("Exact reviewed statement", link.statement) + paragraph("Source locator", link.locator or "Not supplied")
        for comparison in control.context_compatibility.comparisons:
            content += paragraph("Context comparison", comparison.dimension + ": " + comparison.status + "; " + comparison.rationale)
        blocks.append(content + "</article>")
    blocks.append("<h2>Retrieved publication identities</h2><p>Publication existence is distinct from statement entailment. Abstracts and full text are omitted.</p>")
    for item in project.evidence:
        content = "<article><h3>" + esc(item.title or "Title unavailable") + "</h3>" + paragraph("Source", item.source)
        content += paragraph("Authors and year", "; ".join(item.authors) + "; " + str(item.year or "unknown"))
        for identifier in item.identifiers:
            url = citation_url(identifier)
            label = identifier.namespace + ": " + identifier.value
            content += f"<p><a rel='noopener noreferrer' href='{esc(url)}'>{esc(label)}</a></p>" if url else paragraph("Identifier", label)
        content += paragraph("Identity status", item.existence_status) + paragraph("Limitations", "; ".join(item.limitations))
        content += paragraph("Licensing", item.licensing_restrictions or "Not determined")
        blocks.append(content + "</article>")
    blocks.append("<h2>Execution results</h2>")
    for result in project.results:
        blocks.append(paragraph("Result", result.result_id + "; " + result.execution_status + "; " + (result.outcome or "No binary interpretation")))
        if result.effect_estimate:
            blocks.append(paragraph(result.effect_estimate.name, result.effect_estimate.value))
        if result.p_value is not None:
            blocks.append(paragraph("Permutation p value", result.p_value))
        if result.confidence_interval:
            interval = result.confidence_interval
            blocks.append(paragraph("Confidence interval", f"{interval.lower} to {interval.upper}; coverage {interval.coverage}; {interval.method}"))
        if result.null_distribution_summary:
            null = result.null_distribution_summary
            blocks.append(paragraph("Null distribution", f"{null.draws} assignments; mean {null.mean}; standard deviation {null.standard_deviation}; {null.null_hypothesis}"))
        blocks.append(paragraph("Scientific assumptions", "; ".join(result.interpretive_metadata)) +
            paragraph("Warnings", "; ".join(result.warnings)) + paragraph("Random seed", result.random_seed) +
            paragraph("Input hashes", "; ".join(item.input_id + ": " + item.sha256 for item in result.input_hashes)) +
            paragraph("Observed software", "; ".join(item.name + ": " + item.version for item in result.software_versions)))
        blocks.append(paragraph("Interpretation", result.interpretation or "No interpretation supplied."))
    blocks.append("<h2>Adversarial assessment</h2>")
    for audit in project.audits:
        blocks.append(paragraph("Assessment", audit.assessment) + paragraph("Rationale", audit.rationale) +
                      paragraph("Uncertainties", "; ".join(audit.uncertainties)) + paragraph("Limitations", "; ".join(audit.limitations)))
    blocks.append("<h2>Network audit</h2>")
    if not network_audit:
        blocks.append("<p>No external requests were recorded in this run.</p>")
    for event in network_audit:
        blocks.append(paragraph("Destination and purpose", event["url"] + "; " + event["purpose"]) +
                      paragraph("Request", event["request_sha256"] + "; " + event["status"]))
        blocks.append(paragraph("Time and transmission", event.get("sent_at", "Unknown") + "; " + event.get("payload_transmission", "Unknown")))
        for field in event["fields"]:
            blocks.append(paragraph("Approved outbound field", field["name"] + ": " + field["value"] + " (" + field["classification"] + ")"))
    blocks.append("<h2>Provenance</h2>")
    for event in project.provenance:
        blocks.append(paragraph(event.action, event.recorded_at.isoformat() + "; " + ", ".join(event.record_ids) + "; Controlomics " + event.controlomics_version))
        if event.model:
            blocks.append(paragraph("Proposal provider", event.model.provider + "; " + event.model.model_identifier + "; policy hash " + event.model.prompt_template_sha256))
    css = "body{max-width:1000px;margin:40px auto;padding:0 24px;background:#f4f5f3;color:#182826;font:16px/1.6 system-ui}h1,h2,h3{line-height:1.25}h2{margin-top:36px}article{background:white;border:1px solid #d5ddd8;padding:18px;margin:16px 0;border-radius:8px}p{overflow-wrap:anywhere}.notice{padding:16px;background:#e9eee8;border-left:4px solid #527361}a{color:#245d55}"
    return "<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'\"><title>Controlomics scientific audit</title><style>" + css + "</style></head><body>" + "".join(blocks) + "</body></html>"


def write_report(project, path: Path, network_audit=()):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(project, network_audit), encoding="utf-8", newline="\n")
