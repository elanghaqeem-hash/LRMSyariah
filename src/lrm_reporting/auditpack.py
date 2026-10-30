"""WP7 engineering audit pack with deterministic, sanitized evidence manifest.

This is NOT an APOLO filing, regulatory publication template or bank approval.
"""
from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import dataclass
from typing import Any, Mapping

from lrm_engine.common.canonical import canonical_json


@dataclass(frozen=True)
class ApprovedRunEvidence:
    run_id: str
    reporting_date: str
    run_type: str
    input_sha256: str
    parameter_sha256: str
    result_sha256: str
    engine_version: str
    akad_mapping_version: str
    parameter_set_version: str
    maker_id: str
    checker_id: str
    approved_at_iso: str
    status: str = 'APPROVED'


def make_audit_pack(*, run: ApprovedRunEvidence,
                    dq_summary: Mapping[str, Any],
                    reconciliation: Mapping[str, Any],
                    result: Mapping[str, Any],
                    trace: Mapping[str, Any]) -> bytes:
    """Deterministic ZIP, no raw customer records; all inputs canonical & hash-linked."""
    if run.status != 'APPROVED' or not run.checker_id or run.checker_id == run.maker_id:
        raise ValueError('Only independently approved runs are exportable')
    for key in (run.input_sha256, run.parameter_sha256, run.result_sha256):
        if len(key) != 64 or not all(c in '0123456789abcdef' for c in key):
            raise ValueError('All calculation digests must be valid SHA256')
    if dq_summary.get('status') != 'PASS' or reconciliation.get('status') != 'PASS':
        raise ValueError('DQ and GL reconciliation must both pass')
    output = canonical_json(result)
    if hashlib.sha256(output).hexdigest() != run.result_sha256:
        raise ValueError('Report result hash disagrees with approved result')
    # Explicitly exclude entire original input / PII from portable audit pack.
    evidence = {
        'calculation_run.json': canonical_json(run),
        'dq.json': canonical_json(dq_summary),
        'reconciliation.json': canonical_json(reconciliation),
        'result.json': output,
        'trace.json': canonical_json(trace),
    }
    manifest = {'file_sha256': {name: hashlib.sha256(blob).hexdigest()
                                for name,blob in sorted(evidence.items())},
                'schema': 'lrm-engineering-auditpack-v1',
                'regulatory_filing_approved': False}
    evidence['manifest.json'] = canonical_json(manifest)
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name, blob in sorted(evidence.items()):
            info = zipfile.ZipInfo(name, date_time=(1980,1,1,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o600 << 16
            z.writestr(info,blob)
    return out.getvalue()