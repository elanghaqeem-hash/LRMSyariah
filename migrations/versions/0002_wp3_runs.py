"""WP3 immutable CalculationRun and audit ledger: R13, R16.

Revision ID: 0002_wp3
Revises: 0001_wp2
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_wp3'
down_revision = '0001_wp2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('lrm_calculation_run',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('reporting_date', sa.Date(), nullable=False),
        sa.Column('run_type', sa.String(24), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('maker_id', sa.String(180), sa.ForeignKey('lrm_principal.subject'), nullable=False),
        sa.Column('checker_id', sa.String(180), sa.ForeignKey('lrm_principal.subject')),
        sa.Column('engine_version', sa.String(60), nullable=False),
        sa.Column('parameter_set_version', sa.String(120), nullable=False),
        sa.Column('akad_mapping_version', sa.String(120), nullable=False),
        sa.Column('scenario_id', sa.String(120)),
        sa.Column('input_sha256', sa.String(64), nullable=False),
        sa.Column('parameter_sha256', sa.String(64), nullable=False),
        sa.Column('input_snapshot', sa.Text(), nullable=False),
        sa.Column('parameter_snapshot', sa.Text(), nullable=False),
        sa.Column('result_snapshot', sa.Text()),
        sa.Column('result_sha256', sa.String(64)),
        sa.Column('dq_summary', sa.Text()), sa.Column('recon_summary', sa.Text()),
        sa.Column('supersedes_run_id', sa.String(36), sa.ForeignKey('lrm_calculation_run.id'), unique=True),
        sa.Column('change_reason', sa.Text()),
        sa.Column('submitted_at', sa.DateTime(timezone=True)),
        sa.Column('approved_at', sa.DateTime(timezone=True)),
        sa.Column('rejected_at', sa.DateTime(timezone=True)),
        sa.Column('rejection_reason', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('DRAFT','VALIDATED','SUBMITTED','APPROVED','REJECTED')", name='ck_run_status'),
        sa.CheckConstraint("run_type IN ('LCR_DAILY','LCR_MONTHLY','NSFR_MONTHLY','NSFR_QUARTERLY','STRESS','SURVIVAL','DCR')", name='ck_run_type'),
        sa.CheckConstraint('checker_id IS NULL OR checker_id <> maker_id', name='ck_run_four_eyes'),
        sa.CheckConstraint("status <> 'APPROVED' OR (checker_id IS NOT NULL AND approved_at IS NOT NULL AND result_sha256 IS NOT NULL)", name='ck_run_approval'),
        sa.CheckConstraint('supersedes_run_id IS NULL OR supersedes_run_id <> id', name='ck_no_self_supersession'),
    )
    op.create_table('lrm_audit_event',
        sa.Column('sequence', sa.Integer(), primary_key=True),
        sa.Column('occurred_at', sa.String(32), nullable=False),
        sa.Column('actor_id', sa.String(180), nullable=False),
        sa.Column('event_type', sa.String(60), nullable=False),
        sa.Column('object_id', sa.String(36), nullable=False),
        sa.Column('metadata_json', sa.Text(), nullable=False),
        sa.Column('previous_hash', sa.String(64), nullable=False),
        sa.Column('event_hash', sa.String(64), nullable=False, unique=True),
    )
    # Database-level protection even against direct UPDATE/DELETE by application role.
    op.execute("""CREATE OR REPLACE FUNCTION lrm_guard_run() RETURNS trigger AS $$
    DECLARE role_name text; trusted_subject text;
    BEGIN
        trusted_subject := current_setting('lrm.actor_id', true);
        SELECT role INTO role_name FROM lrm_principal WHERE subject=trusted_subject AND enabled;
        IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Calculation runs cannot be deleted'; END IF;
        IF TG_OP = 'UPDATE' AND OLD.status = 'APPROVED' THEN
            RAISE EXCEPTION 'Approved calculation run is immutable';
        END IF;
        IF TG_OP = 'INSERT' THEN
            IF role_name IS DISTINCT FROM 'MAKER' OR NEW.maker_id IS DISTINCT FROM trusted_subject OR NEW.status <> 'DRAFT' THEN
                RAISE EXCEPTION 'Only authenticated maker may create draft'; END IF;
            IF NEW.supersedes_run_id IS NOT NULL THEN
                IF NOT EXISTS(SELECT 1 FROM lrm_calculation_run p WHERE p.id=NEW.supersedes_run_id AND p.status='APPROVED' AND p.run_type=NEW.run_type AND p.reporting_date=NEW.reporting_date)
                OR NEW.change_reason IS NULL OR btrim(NEW.change_reason) = '' THEN
                    RAISE EXCEPTION 'Supersession requires approved same-type and date predecessor'; END IF;
            END IF;
        ELSIF TG_OP = 'UPDATE' THEN
            IF OLD.maker_id IS DISTINCT FROM NEW.maker_id
               OR OLD.input_sha256 IS DISTINCT FROM NEW.input_sha256
               OR OLD.parameter_sha256 IS DISTINCT FROM NEW.parameter_sha256
               OR OLD.input_snapshot IS DISTINCT FROM NEW.input_snapshot
               OR OLD.parameter_snapshot IS DISTINCT FROM NEW.parameter_snapshot
               OR OLD.engine_version IS DISTINCT FROM NEW.engine_version
               OR OLD.akad_mapping_version IS DISTINCT FROM NEW.akad_mapping_version
               OR OLD.parameter_set_version IS DISTINCT FROM NEW.parameter_set_version THEN
               RAISE EXCEPTION 'Calculation input and provenance immutable from creation';
            END IF;
            IF OLD.status = 'DRAFT' AND NEW.status = 'VALIDATED' OR OLD.status = 'VALIDATED' AND NEW.status = 'SUBMITTED' THEN
               IF role_name IS DISTINCT FROM 'MAKER' OR NEW.maker_id IS DISTINCT FROM trusted_subject THEN RAISE EXCEPTION 'Maker-only transition'; END IF;
            ELSIF OLD.status = 'SUBMITTED' AND NEW.status IN ('APPROVED','REJECTED') THEN
               IF role_name IS DISTINCT FROM 'CHECKER' OR trusted_subject=NEW.maker_id OR NEW.checker_id IS DISTINCT FROM trusted_subject THEN RAISE EXCEPTION 'Independent checker required'; END IF;
            ELSE RAISE EXCEPTION 'Invalid run transition'; END IF;
        END IF;
        RETURN NEW;
    END $$ LANGUAGE plpgsql""")
    op.execute("CREATE TRIGGER trg_lrm_run_guard BEFORE INSERT OR UPDATE OR DELETE ON lrm_calculation_run FOR EACH ROW EXECUTE FUNCTION lrm_guard_run()")
    op.execute("""CREATE OR REPLACE FUNCTION lrm_audit_append_only() RETURNS trigger AS $$
    BEGIN RAISE EXCEPTION 'Audit events cannot be altered or deleted'; END $$ LANGUAGE plpgsql""")
    op.execute("CREATE TRIGGER trg_lrm_audit_immutable BEFORE UPDATE OR DELETE ON lrm_audit_event FOR EACH ROW EXECUTE FUNCTION lrm_audit_append_only()")
    # A dedicated application DB role must not own tables or have TRUNCATE privileges.


def downgrade() -> None:
    raise RuntimeError('WP3 irreversible migration: audit trail must be retained; restore controlled backup')