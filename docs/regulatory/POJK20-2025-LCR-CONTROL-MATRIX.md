# LCR BUS/UUS — Regulatory Traceability & Independent Validation Register

**Date:** 31 October 2026  
**Official source:** [OJK POJK No. 20/2025 official regulation and Lampiran I](https://ojk.go.id/id/regulasi/Pages/POJK-20-Tahun-2025-Kewajiban-Pemenuhan-Rasio-Kecukupan-Likuiditas-dan-Rasio-Pendanaan-Stabil-Bersih-Bagi-BUS-UUS.aspx).  
**Basis:** PDF regulatory source, NOT the older conventional-bank Bank Banten proposal.  
**Status convention:** `TEXT_VERIFIED` = legal text checked against published OJK PDF; `MATH_TESTED` = specific pure arithmetic checked with synthetic tests; `BANK_HOLD` = implementation cannot be certified without Bank evidence; **never interpret TEXT_VERIFIED as Bank/DPS sign-off.**

## Regulatory controls and implementation gaps

| ID | POJK20/2025 Lampiran I reference | Rule verified from official OJK PDF | Engine and evidence status | Acceptance evidence missing / action |
|---|---|---|---|---|
| REG-LCR-01 | Pasal 2, 5, Lampiran I III.A | HQLA must be eligible, available, market-valued and unencumbered, satisfying fundamental, market, operational and diversification requirements | TEXT_VERIFIED / BANK_HOLD | Security master, independent pricing, encumbrance & right-to-rehypothecate status, issuer/market eligibility tests, signed valuation policy |
| REG-LCR-02 | Lampiran I III.B.1 | L1 market-valued without haircut; various OJK/BIS/sovereign instruments subject to detailed exceptions and FX constraints | TEXT_VERIFIED / BANK_HOLD | Asset-by-asset eligibility; system cannot infer from akad alone |
| REG-LCR-03 | Lampiran I III.B.2 | L2A haircut 15%; eligibility tied to risk weight/rating/market and concentration controls | TEXT_VERIFIED / BANK_HOLD | Asset metadata, trading depth, eligible issuer and Bank approval |
| REG-LCR-04 | Lampiran I III.B.3 | 2B residential sharia ABS haircut 25%; specified corporate/sovereign/equity instruments haircut 50%, subject to eligibility | TEXT_VERIFIED / BANK_HOLD | Instrument type, rating, issuer, collateral pool, risk retention, non-financial issuer, market stress evidence; review any other 2B sukuk case separately |
| REG-LCR-05 | Pasal 6(3)(4); Lampiran I III.C.1 | L2B deduction = max(adjusted L2B−15/85(adjusted L1+adjusted L2A), adjusted L2B−15/60(stock L1), 0) | TEXT_VERIFIED / MATH_TESTED | Pure-engine helper added; Bank must certify adjusted levels sourced from SFT ledger |
| REG-LCR-06 | Lampiran I III.C.2 | L2 aggregate deduction = max(adjusted L2A+adjusted L2B−deduction L2B−2/3(adjusted L1), 0) | TEXT_VERIFIED / MATH_TESTED | Compare daily Bank golden paper; no numeric rounding before export |
| REG-LCR-07 | Lampiran I III.C.3-6 | Unwind applies to short-term SFT involving qualifying HQLA, including cash, maturity up to 30 days | TEXT_VERIFIED / BANK_HOLD | Signed SFT transaction ledger: settled principal, start/end, maturity, counterparties, security IDs, enforceability, collateral and haircut. Current 13-file source lacks this. Keep operational unwind **fail closed** |
| REG-LCR-08 | Pasal 8; Lampiran I IV.A.1 | Retail stable deposits/investment 5%, less stable 10%; stability also depends on LPS and transaction/relationship and DCR profit smoothing conditions | TEXT_VERIFIED / BANK_HOLD | LPS coverage verified, relationship product evidence, routine usage, DCR/PER policy and premature withdrawals/pledges |
| REG-LCR-09 | Lampiran I IV.A.2 | UMK funding classes, stable/less stable treatment with conditional segmentation | TEXT_VERIFIED / BANK_HOLD | Business size proof, connected-client aggregation, LPS, deposit stability and customer segment certification |
| REG-LCR-10 | Lampiran I IV.A.3 | Corporate operational 5% insured/25% uninsured; government & other qualifying nonoperational funding 20% insured/40% uninsured, financial institutions mostly 100% | TEXT_VERIFIED / BANK_HOLD | Bank signed operational account methodology, LPS and counterparty classification, restricted investment exception |
| REG-LCR-11 | Lampiran I IV.A.3, RPSIA | RPSIA outflow 0% for no early withdrawal or notice >=30 days; 40% when notice <30 days | TEXT_VERIFIED / BANK_HOLD | Contractual notice, withdrawal clauses, Sharia/DPS approval |
| REG-LCR-12 | Lampiran I IV.A.4 | Secured funding by collateral grade/counterparty: 0%,15%,25%,50%,100% categories | TEXT_VERIFIED / BANK_HOLD | Actual repo/SiPA secured funding ledger and legally validated collateral mapping |
| REG-LCR-13 | Lampiran I IV.A.5 | Additional requirements: Sharia derivatives, collateral, structured finance, undrawn credit vs liquidity facility drawdowns, guarantees/LC and contractual outflows | TEXT_VERIFIED / BANK_HOLD | Undrawn balances, unconditional revocability, counterparty type, derivative netting, trade-finance category, collateral liabilities |
| REG-LCR-14 | Lampiran I IV.B | Inflows <=75% of gross outflows; inflows contractual, performing/non-default, exclude HQLA double counting and committed inflow facilities | TEXT_VERIFIED / BANK_HOLD | Source identification for HQLA vs receivable, Kolektibilitas=1, expected non-default, 30-day contractual cashflows incl. settlement |
| REG-LCR-15 | Lampiran I IV.B.1 | Secured financing inflow factor depends on received collateral: 0/15/25/50/100%, special 0% if collateral used for short covering | TEXT_VERIFIED / BANK_HOLD | SFT/reverse-repo ledger and received collateral use; missing in current 13 contracts |
| REG-LCR-16 | Lampiran I IV.B.2 | Retail/UMK performing-financing inflow 50%; financial institutions/BI performing financing 100%; other nonfinancial performing financing 50%; operational interbank placements 0% | TEXT_VERIFIED / BANK_HOLD | Counterparty lookup, cashflow-level schedule, rolled facilities and default filters |
| REG-LCR-17 | Pasal 2(5), 12; transition | IDR and separate meaningful FX analyses/Bank reporting dates, daily source for period disclosure | TEXT_VERIFIED / BANK_HOLD | Approved FX rates and significant currency thresholds, daily engine outputs and disclosure pack |
| REG-LCR-18 | Lampiran I and publication/reporting requirements | Audit must trace each mapped GL/product/akad to its official category & effective rate | ENGINEERING_PARTIAL / BANK_HOLD | Bank actual GL/akad mapping, checker & SKMR signed scope, independent working papers |
| REG-LCR-19 | Bank control (not numerical POJK factor) | Daily GL reconciliation and underwriting of mismatches | ENGINEERING_PARTIAL / BANK_HOLD | Three-way reconciliation gross now available; gross market value vs book basis reconciled separately; cross-file cashflow alignment and exception handling independent review |
| REG-LCR-20 | Regulatory model risk/control | Independent validation and production approval cannot be self-declared | BANK_HOLD | Independent validator, evidence of test vectors, parallel daily Bank working paper, SKMR/Finance/DPS/TI written decisions |

### Critical compliance findings

- **P0-REG-01:** Existing simple cap allocation may give the same total for an unadjusted portfolio but is **not an implementation of Annex I III.C when adjusted stock differs due to SFT**. New pure arithmetic implements the exact two-deduction formula. It does **not** source or approve adjusted levels.
- **P0-REG-02:** No independent evidence of HQLA fundamental/operational eligibility; `HQLA:L1` mapping alone insufficient.
- **P0-REG-03:** Missing SFT/reverse-repo transactional ledger for adjusted unwind, secured funding/outflow and secured financing inflow, so Bank production must block.
- **P0-REG-04:** Stable retail / UMK DCR/PER and operational corporate determination cannot be decided reliably from 13 source schema fields.
- **P0-REG-05:** Existing LCR pipeline maps some financing inflows without independent performing/default/committed facility evidence; missing categorization evidence means ratio not certified.
- **P0-REG-06:** Actual bank GL, reconciled paper, data vault, model validation, 1-quarter daily parallel run, approvals not available in project materials. Fake approvals are prohibited.

## Exact cap formula trace

The Annex III.C **two adjustments** are mathematically distinct from a naive `min(Level2,40%)` when short-term unwind changes adjusted levels. Post-haircut original holdings are `L1, L2A, L2B`. Adjusted holdings following SFT unwind are `A1, A2A, A2B`.

```
deduction_2B = max(A2B - (15/85)*(A1 + A2A), A2B - (15/60)*L1, 0)
deduction_2  = max(A2A + A2B - deduction_2B - (2/3)*A1, 0)
HQLA         = L1 + L2A + L2B - deduction_2B - deduction_2
```

All components after *haircut*; calculation uses `Decimal` and Bank/independent validator signoff remains required. The helper has independent unit tests but does not assert source transaction eligibility.

## Evidence register for Bank (vault only; do not upload customer/GL data to public GitHub)

| Owner | Required evidence | Current state |
|---|---|---|
| Treasury/Finance | Signed and effective GL mapping, account signs, cash flows, OJK report & source extract control totals | **NOT PROVIDED** |
| Risk/SKMR | Official rule-to-account mapping, 30-day stress methodology, HQLA and ratio independent golden working papers | **NOT PROVIDED** |
| Syariah/DPS | Effective akad-to-LCR and DCR/PER classification, secured SFT and restricted profit-sharing product treatment | **NOT PROVIDED** |
| Finance/Treasury/Legal | SFT / repo sharia contracts, collateral ledger, 30-day unwind, encumbrance and haircut testing | **NOT PROVIDED** |
| IT/InfoSec | Bank PostgreSQL restricted role, IDP/SSO, extract vault, encryption, SIEM & backup/restore evidence | **NOT PROVIDED** |
| Independent validation | Challenge cases, reruns, exception findings and model validation signoff | **NOT PROVIDED** |

**Decision:** REGULATORY ACCEPTANCE HOLD. This register is an evidence-based review of accessible official text and public source code, not an independent Bank-certified model validation or a statement of conformity.