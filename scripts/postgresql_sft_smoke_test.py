"""Throwaway PostgreSQL 16 only: real SFT ledger insert, immutability and bindings."""
from __future__ import annotations

import os
import uuid
from dataclasses import asdict
from datetime import date,timedelta
from decimal import Decimal

from sqlalchemy import create_engine,text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session

from lrm_engine.common.canonical import sha256_canonical
from lrm_engine.lcr.sft_ledger import SFTLedger,SFTTrade,UnwindLeg,stock_fingerprint
from lrm_services.models import Principal
from lrm_services.runs import RunService
from lrm_services.sft_repository import attach_sft_ledger,verify_sft_ledger_bound


def main() -> None:
    url=os.getenv("LRM_DATABASE_URL", "")
    if "localhost" not in url or "lrm_ci" not in url:
        raise RuntimeError("SFT smoke permitted only in isolated lrm_ci database")
    engine=create_engine(url)
    maker="sft-maker-"+uuid.uuid4().hex[:12]
    d=date(2026,10,31)
    sha="a"*64
    stock={"L1":Decimal("100"),"L2A":Decimal("10"),"L2B":Decimal("0")}
    try:
        with Session(engine) as s:
            s.add(Principal(subject=maker,role="MAKER",enabled=True))
            s.commit()
            trade=SFTTrade(trade_id="SFT-12345678",trade_kind="REPO_SYARIAH",akad="wakalah",
                trade_date=d-timedelta(days=10),settlement_date=d-timedelta(days=9),
                maturity_date=d+timedelta(days=14),currency="IDR",state="SETTLED_OPEN",
                signed_contract_sha256=sha,settlement_sha256=sha,
                legal_sharia_ref="SYNTHETIC-DPS-TEST",legs=(
                  UnwindLeg(leg_id="LEG-12345678",asset_id="ASSET-12345678",level="L1",
                    movement="RETURN_TO_COUNTERPARTY",post_haircut_value=Decimal(20),
                    counted_in_current_stock=True,security_eligibility_ref="synthetic-e1",
                    independent_price_ref="synthetic-p1",custody_encumbrance_ref="synthetic-c1",
                    source_sha256=sha),
                  UnwindLeg(leg_id="LEG-12345679",asset_id="ASSET-12345679",level="L2A",
                    movement="RETURN_FROM_COUNTERPARTY",post_haircut_value=Decimal(15),
                    counted_in_current_stock=False,security_eligibility_ref="synthetic-e2",
                    independent_price_ref="synthetic-p2",custody_encumbrance_ref="synthetic-c2",
                    source_sha256=sha)))
            ledger=SFTLedger(reporting_date=d,reporting_currency="IDR",source_batch_sha256=sha,
                hqla_stock_sha256=stock_fingerprint(stock),bank_sft_policy_ref="synthetic-policy",
                bank_sft_policy_sha256=sha,trades=(trade,))
            inputs={"legs":[],"reporting_date":d,"reporting_currency":"IDR",
                 "has_unwind_transactions":True,"sft_ledger":asdict(ledger),
                 "sft_ledger_sha256":sha256_canonical(ledger)}
            run=RunService(s,maker).create(reporting_date=d,run_type="LCR_DAILY",
                  engine_version="0.4.1+abcdef123456",parameter_set_version="synthetic-param",
                  akad_mapping_version="synthetic-akad",input_data=inputs,parameters={"synthetic":True})
            run_id=run.id
            attached=attach_sft_ledger(s,maker,run,ledger)
            assert verify_sft_ledger_bound(s,run)==attached.ledger_sha256
            s.commit()
        for sql in (
            "UPDATE lrm_sft_run_ledger SET trade_count=999 WHERE run_id=:rid",
            "DELETE FROM lrm_sft_run_ledger WHERE run_id=:rid"):
            try:
                with engine.begin() as c:
                    c.execute(text(sql),{"rid":run_id})
            except DatabaseError:
                continue
            raise AssertionError("SFT evidence DB write protection failed")
        print("PASS: real isolated PG SFT append-only, hash proof and raw-DML rejects")
    finally:
        engine.dispose()


if __name__=="__main__":
    main()