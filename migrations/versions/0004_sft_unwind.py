"""Append-only SFT/repo collateral ledger bound to LCR proof.

Revision ID: 0004_sft_unwind
Revises: 0003_wp45
Bank deployment remains HOLD until Bank restricted-role and model UAT.
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_sft_unwind"
down_revision = "0003_wp45"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("lrm_sft_run_ledger",
        sa.Column("run_id",sa.String(36),sa.ForeignKey("lrm_calculation_run.id"),primary_key=True),
        sa.Column("maker_id",sa.String(180),sa.ForeignKey("lrm_principal.subject"),nullable=False),
        sa.Column("position_date",sa.Date(),nullable=False),
        sa.Column("source_batch_sha256",sa.String(64),nullable=False),
        sa.Column("stock_sha256",sa.String(64),nullable=False),
        sa.Column("ledger_sha256",sa.String(64),nullable=False),
        sa.Column("trade_count",sa.Integer(),nullable=False),
        sa.Column("snapshot_json",sa.Text(),nullable=False),
        sa.CheckConstraint("trade_count > 0",name="ck_sft_trade_count"),
    )
    op.execute("""CREATE FUNCTION lrm_sft_immutable_guard() RETURNS trigger AS $$
    DECLARE role_name text; run_maker text; run_state text;
    BEGIN
      IF TG_OP <> 'INSERT' THEN RAISE EXCEPTION 'SFT evidence is append-only'; END IF;
      SELECT role INTO role_name FROM lrm_principal
       WHERE enabled AND subject=current_setting('lrm.actor_id',true);
      SELECT maker_id,status INTO run_maker,run_state FROM lrm_calculation_run
       WHERE id=NEW.run_id;
      IF role_name IS DISTINCT FROM 'MAKER' OR run_maker IS DISTINCT FROM NEW.maker_id
       OR NEW.maker_id IS DISTINCT FROM current_setting('lrm.actor_id',true)
       OR run_state IS DISTINCT FROM 'DRAFT' THEN
        RAISE EXCEPTION 'SFT ledger requires owner maker on draft run';
      END IF;
      RETURN NEW;
    END $$ LANGUAGE plpgsql""")
    op.execute("""CREATE TRIGGER trg_lrm_sft_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON lrm_sft_run_ledger
        FOR EACH ROW EXECUTE FUNCTION lrm_sft_immutable_guard()""")
    op.execute("""CREATE FUNCTION lrm_sft_run_guard() RETURNS trigger AS $$
    DECLARE ledger_hash text; input_flag text;
    BEGIN
      IF NEW.run_type NOT IN ('LCR_DAILY','LCR_MONTHLY')
        OR NEW.status NOT IN ('VALIDATED','APPROVED') THEN RETURN NEW; END IF;
      input_flag := NEW.input_snapshot::jsonb ->> 'has_unwind_transactions';
      IF input_flag IS DISTINCT FROM 'true' THEN RETURN NEW; END IF;
      SELECT ledger_sha256 INTO ledger_hash FROM lrm_sft_run_ledger WHERE run_id=NEW.id;
      IF ledger_hash IS NULL OR ledger_hash IS DISTINCT FROM
          NEW.input_snapshot::jsonb ->> 'sft_ledger_sha256' THEN
        RAISE EXCEPTION 'Validated SFT LCR requires an immutable matching collateral ledger';
      END IF;
      RETURN NEW;
    END $$ LANGUAGE plpgsql""")
    op.execute("""CREATE TRIGGER trg_lrm_sft_run_guard
        BEFORE UPDATE ON lrm_calculation_run FOR EACH ROW
        EXECUTE FUNCTION lrm_sft_run_guard()""")


def downgrade() -> None:
    raise RuntimeError("Cannot destructively downgrade immutable SFT evidence")