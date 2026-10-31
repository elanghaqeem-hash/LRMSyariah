"""Append-only evidence-bound LCR and GL case review for issue #4.

Revision ID: 0003_wp45
Revises: 0002_wp3
This migration requires independently restricted PostgreSQL application roles.
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_wp45"
down_revision = "0002_wp3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("lrm_lcr_run_evidence",
        sa.Column("run_id", sa.String(36), sa.ForeignKey("lrm_calculation_run.id"), primary_key=True),
        sa.Column("maker_id", sa.String(180), sa.ForeignKey("lrm_principal.subject"), nullable=False),
        sa.Column("input_sha256", sa.String(64), nullable=False),
        sa.Column("parameter_sha256", sa.String(64), nullable=False),
        sa.Column("evidence_sha256", sa.String(64), nullable=False),
        sa.Column("evidence_json", sa.Text(), nullable=False),
        sa.CheckConstraint("length(evidence_sha256)=64", name="ck_lcr_evidence_sha"),
    )
    op.create_table("lrm_lcr_recon_case",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("lrm_calculation_run.id"), nullable=False),
        sa.Column("gl_code", sa.String(100), nullable=False),
        sa.Column("variance_json", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(12), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("checker_id", sa.String(180), sa.ForeignKey("lrm_principal.subject")),
        sa.Column("checker_comment", sa.Text()),
        sa.CheckConstraint("status in ('OPEN','REVIEWED')", name="ck_lcr_case_status"),
        sa.CheckConstraint("severity in ('HIGH','CRITICAL')", name="ck_lcr_case_severity"),
    )
    op.create_index("ix_lrm_lcr_recon_case_run", "lrm_lcr_recon_case", ["run_id"])
    op.execute("""CREATE FUNCTION lrm_lcr_evidence_guard() RETURNS trigger AS $$
    DECLARE role_name text; run_maker text; run_state text;
    BEGIN
      IF TG_OP <> 'INSERT' THEN RAISE EXCEPTION 'LCR evidence is append-only'; END IF;
      SELECT role INTO role_name FROM lrm_principal
         WHERE subject=current_setting('lrm.actor_id', true) AND enabled;
      SELECT maker_id, status INTO run_maker,run_state FROM lrm_calculation_run WHERE id=NEW.run_id;
      IF role_name IS DISTINCT FROM 'MAKER' OR NEW.maker_id IS DISTINCT FROM current_setting('lrm.actor_id', true)
         OR run_maker IS DISTINCT FROM NEW.maker_id OR run_state IS DISTINCT FROM 'DRAFT' THEN
         RAISE EXCEPTION 'Only owner maker may insert LCR proof for draft'; END IF;
      RETURN NEW;
    END $$ LANGUAGE plpgsql""")
    op.execute("""CREATE TRIGGER trg_lrm_lcr_evidence_guard
      BEFORE INSERT OR UPDATE OR DELETE ON lrm_lcr_run_evidence
      FOR EACH ROW EXECUTE FUNCTION lrm_lcr_evidence_guard()""")
    op.execute("""CREATE FUNCTION lrm_lcr_run_proof_guard() RETURNS trigger AS $$
    DECLARE p record; snapshot jsonb;
    BEGIN
      IF NEW.run_type NOT IN ('LCR_DAILY','LCR_MONTHLY') THEN RETURN NEW; END IF;
      IF NEW.status NOT IN ('VALIDATED','APPROVED') THEN RETURN NEW; END IF;
      SELECT * INTO p FROM lrm_lcr_run_evidence WHERE run_id=NEW.id;
      IF NOT FOUND OR p.maker_id IS DISTINCT FROM NEW.maker_id
         OR p.input_sha256 IS DISTINCT FROM NEW.input_sha256
         OR p.parameter_sha256 IS DISTINCT FROM NEW.parameter_sha256 THEN
         RAISE EXCEPTION 'LCR run requires input-bound immutable evidence'; END IF;
      snapshot := p.evidence_json::jsonb;
      IF snapshot #>> '{dq,status}' <> 'PASS' OR snapshot #>> '{recon,status}' <> 'PASS'
         OR snapshot ->> 'mapping_sha256' IS DISTINCT FROM NEW.akad_mapping_version
         OR snapshot ->> 'parameter_set_hash' IS DISTINCT FROM NEW.parameter_set_version
         OR snapshot #>> '{recon,date}' IS DISTINCT FROM to_char(NEW.reporting_date, 'YYYY-MM-DD') THEN
         RAISE EXCEPTION 'LCR DQ/recon/parameter verification failed'; END IF;
      RETURN NEW;
    END $$ LANGUAGE plpgsql""")
    op.execute("""CREATE TRIGGER trg_lrm_lcr_run_proof_guard
      BEFORE UPDATE ON lrm_calculation_run FOR EACH ROW
      EXECUTE FUNCTION lrm_lcr_run_proof_guard()""")
    op.execute("""CREATE FUNCTION lrm_lcr_recon_case_guard() RETURNS trigger AS $$
    DECLARE role_name text; maker_subject text;
    BEGIN
      IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'LCR recon case cannot be deleted'; END IF;
      SELECT role INTO role_name FROM lrm_principal
         WHERE subject=current_setting('lrm.actor_id', true) AND enabled;
      IF TG_OP = 'INSERT' THEN
        SELECT maker_id INTO maker_subject FROM lrm_calculation_run WHERE id=NEW.run_id;
        IF role_name IS DISTINCT FROM 'MAKER' OR maker_subject IS DISTINCT FROM current_setting('lrm.actor_id', true)
            OR NEW.status <> 'OPEN' THEN RAISE EXCEPTION 'Only maker opens recon case'; END IF;
      ELSE
        SELECT maker_id INTO maker_subject FROM lrm_calculation_run WHERE id=OLD.run_id;
        IF OLD.status <> 'OPEN' OR NEW.status <> 'REVIEWED'
           OR role_name IS DISTINCT FROM 'CHECKER' OR current_setting('lrm.actor_id', true)=maker_subject
           OR NEW.checker_id IS DISTINCT FROM current_setting('lrm.actor_id', true)
           OR NEW.run_id IS DISTINCT FROM OLD.run_id OR NEW.gl_code IS DISTINCT FROM OLD.gl_code
           OR NEW.variance_json IS DISTINCT FROM OLD.variance_json OR NEW.severity IS DISTINCT FROM OLD.severity THEN
           RAISE EXCEPTION 'Invalid independent recon exception review'; END IF;
      END IF;
      RETURN NEW;
    END $$ LANGUAGE plpgsql""")
    op.execute("""CREATE TRIGGER trg_lrm_lcr_recon_case_guard
      BEFORE INSERT OR UPDATE OR DELETE ON lrm_lcr_recon_case
      FOR EACH ROW EXECUTE FUNCTION lrm_lcr_recon_case_guard()""")


def downgrade() -> None:
    # Destructive rollback is prohibited after evidence creation in production.
    raise RuntimeError("Immutable evidence cannot be downgraded without Bank-authorized recovery procedure")