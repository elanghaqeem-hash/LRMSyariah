"""Bank UAT tool: compare a previously generated LCR result with Bank paper.

Run only inside approved Bank workspace. Does not authenticate Bank signatures:
verify the SHA/sign-off out-of-band before providing these arguments.
Never put actual Bank papers/outputs in public repository or GitHub Actions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from lrm_services.lcr_differential import parse_working_paper_bytes, compare_working_paper


def main() -> int:
    parser=argparse.ArgumentParser(description="Privacy-conscious Bank LCR differential (no raw output)")
    parser.add_argument("--bank-paper",required=True,type=Path)
    parser.add_argument("--engine-result",required=True,type=Path)
    parser.add_argument("--paper-sha256",required=True)
    parser.add_argument("--bank-approval-ref",required=True)
    parser.add_argument("--bank-approval-sha256",required=True)
    parser.add_argument("--date",required=True)
    parser.add_argument("--currency",required=True)
    parser.add_argument("--amount-tolerance",required=True)
    parser.add_argument("--ratio-tolerance",required=True)
    parser.add_argument("--tolerance-approval-ref",required=True)
    parser.add_argument("--synthetic",action="store_true",help="Only explicitly synthetic input")
    args=parser.parse_args()
    paper_bytes=args.bank_paper.read_bytes()
    paper=parse_working_paper_bytes(paper_bytes,expected_sha256=args.paper_sha256,
         approved_ref=args.bank_approval_ref,bank_approved_sha256=args.bank_approval_sha256,
         synthetic_only=args.synthetic)
    engine_bytes=args.engine_result.read_bytes()
    if len(engine_bytes)>2_000_000:
        raise ValueError("Engine result exceeds bounded UAT summary limit")
    engine=json.loads(engine_bytes,parse_float=Decimal)
    result=compare_working_paper(bank=paper,engine=engine,
        reporting_date=date.fromisoformat(args.date),currency=args.currency,
        monetary_tolerance=Decimal(args.amount_tolerance),
        ratio_tolerance=Decimal(args.ratio_tolerance),
        tolerance_approval_ref=args.tolerance_approval_ref)
    # Emit only status and digests. Detailed Bank values stay inside UAT vault.
    print(json.dumps({"status":result.status,"mode":"SYNTHETIC" if args.synthetic else "BANK_REFERENCE_UNVERIFIED_SIGNATURE",
                      "evidence_sha256":result.evidence_sha256,
                      "engine_sha256":result.engine_result_sha256,
                      "bank_paper_sha256":hashlib.sha256(paper_bytes).hexdigest(),
                      "passing":sum(x.status=="PASS" for x in result.differences),
                      "failed":sum(x.status=="FAILED" for x in result.differences)},sort_keys=True))
    return 0 if result.status=="PASS" else 2


if __name__=="__main__":
    raise SystemExit(main())