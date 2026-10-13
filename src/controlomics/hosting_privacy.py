"""Recorded hosted-processing exceptions, separate from active HTTP authorization."""

from __future__ import annotations

from datetime import datetime

from controlomics.project import parse_project_json
from controlomics.schemas import (
    HOSTED_PROCESSING_POLICY_REVISION,
    ControlomicsProject,
    HostedProcessingReceipt,
)

__all__ = (
    "HOSTED_PROCESSING_POLICY_REVISION", "HostedProcessingReceipt",
    "describe_processing_privacy", "record_hosted_processing",
    "hosted_processing_notice", "record_hosted_input_summary", "hosted_processing_receipt",
)


def hosted_processing_receipt(
    *, processor_origin: str, session_binding_sha256: str, granted_at: datetime,
) -> HostedProcessingReceipt:
    """Construct metadata for consent independently verified by the HTTP adapter."""

    return HostedProcessingReceipt(
        processor_origin=processor_origin,
        session_binding_sha256=session_binding_sha256,
        granted_at=granted_at,
    )


def record_hosted_processing(
    project: ControlomicsProject,
    *,
    processor_origin: str,
    session_binding_sha256: str,
    granted_at: datetime,
) -> ControlomicsProject:
    """Record a grant verified by the HTTP adapter without altering scientific records.

    Call only after the adapter independently verifies current signed-session consent.
    A receipt loaded from a project cannot authorize a new request or web session.
    """

    receipt = hosted_processing_receipt(
        processor_origin=processor_origin,
        session_binding_sha256=session_binding_sha256,
        granted_at=granted_at,
    )
    project = parse_project_json(project.model_dump_json())
    existing = project.privacy.hosted_processing_receipts
    if receipt in existing:
        return project
    privacy = project.privacy.model_copy(update={"hosted_processing_receipts": existing + (receipt,)})
    return parse_project_json(project.model_copy(update={"privacy": privacy}).model_dump_json())


def hosted_processing_notice(receipt: HostedProcessingReceipt) -> str:
    """Describe a historical attestation without asserting authenticated provenance."""

    return (
        "A recorded session consent attests to temporary first-party processing at "
        + receipt.processor_origin + " under policy " + receipt.policy_revision
        + ", granted at " + receipt.granted_at.isoformat()
        + ". This exception covers project records, supplied source-review text, numeric inputs, "
        "and evaluation records in request memory and owned execution temporary directories. "
        "It permits no saved projects or uploads and no project or raw-input forwarding to providers. "
        "Ordinary cleanup is attempted; crash cleanup is not guaranteed. "
        "Imported receipts are unauthenticated historical attestations and grant no active session permission."
    )


def describe_processing_privacy(project: ControlomicsProject) -> str:
    """Report baseline policy and recorded exceptions without guessing execution location."""

    if not project.privacy.hosted_processing_receipts:
        return project.privacy.classification + "; project and raw inputs remain local"
    return (
        project.privacy.classification
        + "; the local-only storage and control flags describe the default local baseline. "
        "This snapshot contains a separately recorded exception for temporary first-party hosted "
        "processing. Persistent project exports remain with the researcher; project and raw-input "
        "forwarding to external providers remains prohibited. The recorded origins and grants below "
        "describe historical processing and do not assert where this report was generated."
    )


def record_hosted_input_summary(summary, receipt: HostedProcessingReceipt):
    """Append a typed input-summary disclosure while preserving the numeric observations."""

    from controlomics.inputs import NumericInputSummary

    validated = NumericInputSummary.model_validate_json(summary.model_dump_json())
    receipt = HostedProcessingReceipt.model_validate_json(receipt.model_dump_json())
    notice = hosted_processing_notice(receipt)
    if notice in validated.limitations:
        return validated
    return NumericInputSummary.model_validate_json(validated.model_copy(
        update={"limitations": validated.limitations + (notice,)}).model_dump_json())
