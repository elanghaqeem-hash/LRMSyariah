"""WP2 governed parameter + akad mapping revision register.

Revision ID: 0001_wp2
Revises:
Created: 2026-10-30
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)

revision = '0001_wp2'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('lrm_principal',
        Column('subject', String(180), primary_key=True),
        Column('role', String(24), nullable=False),
        Column('enabled', Boolean(), nullable=False),
        CheckConstraint("role in ('MAKER','CHECKER','AUDITOR','ADMINISTRATOR','ALCO')",
                        name='ck_principal_role'))
    op.create_table('lrm_governed_revision',
        Column('id', String(36), primary_key=True),
        Column('kind', String(20), nullable=False),
        Column('item_key', String(260), nullable=False),
        Column('version', Integer(), nullable=False),
        Column('status', String(25), nullable=False),
        Column('effective_from', Date(), nullable=False),
        Column('effective_to', Date(), nullable=True),
        Column('payload_json', Text(), nullable=False),
        Column('legal_basis', Text(), nullable=False),
        Column('change_reason', Text(), nullable=False),
        Column('retirement', Boolean(), nullable=False),
        Column('maker_id', String(180), ForeignKey('lrm_principal.subject'), nullable=False),
        Column('checker_id', String(180), ForeignKey('lrm_principal.subject')),
        Column('rejected_by_id', String(180), ForeignKey('lrm_principal.subject')),
        Column('source_document_sha256', String(64)),
        Column('verification_ref', Text()),
        Column('syariah_review_ref', Text()),
        Column('submitted_at', DateTime(timezone=True)),
        Column('approved_at', DateTime(timezone=True)),
        Column('rejected_at', DateTime(timezone=True)),
        Column('rejection_reason', Text()),
        Column('created_at', DateTime(timezone=True)),
        UniqueConstraint('kind','item_key','version', name='uq_revision_version'),
        CheckConstraint("kind IN ('PARAMETER','MAPPING')", name='ck_revision_kind'),
        CheckConstraint("status IN ('DRAFT_UNVERIFIED','PENDING','ACTIVE','RETIRED')",
                        name='ck_revision_status'),
        CheckConstraint('effective_to IS NULL OR effective_to >= effective_from',
                        name='ck_revision_dates'),
        CheckConstraint('checker_id IS NULL OR checker_id <> maker_id',
                        name='ck_revision_four_eyes'),
        CheckConstraint("status NOT IN ('ACTIVE','RETIRED') OR "
                        "(checker_id IS NOT NULL AND approved_at IS NOT NULL "
                        "AND submitted_at IS NOT NULL)",
                        name='ck_revision_approval_fields'),
        CheckConstraint("status <> 'ACTIVE' OR retirement = false",
                        name='ck_revision_active_nonretirement'),
        CheckConstraint("status <> 'RETIRED' OR retirement = true",
                        name='ck_revision_retired_tombstone'),
        CheckConstraint("status <> 'ACTIVE' OR kind <> 'PARAMETER' OR "
                        "(source_document_sha256 IS NOT NULL AND verification_ref IS NOT NULL)",
                        name='ck_parameter_verified'),
        CheckConstraint("status <> 'ACTIVE' OR kind <> 'MAPPING' OR syariah_review_ref IS NOT NULL",
                        name='ck_mapping_sharia_review'))
    op.create_index('ix_rev_effective_lookup', 'lrm_governed_revision',
                    ['kind','item_key','effective_from'])
    op.execute("CREATE UNIQUE INDEX uq_approved_same_date ON lrm_governed_revision "
               "(kind, item_key, effective_from) WHERE status IN ('ACTIVE','RETIRED')")
    # Native PostgreSQL trigger blocks direct SQL privilege bypass as well as ORM writes.
    op.execute("""
    CREATE OR REPLACE FUNCTION lrm_enforce_revision_guard() RETURNS trigger AS $$
    DECLARE
       role_name text;
       trusted_subject text;
       max_approved_from date;
    BEGIN
      IF TG_OP IN ('UPDATE','DELETE') AND OLD.status IN ('ACTIVE','RETIRED') THEN
        RAISE EXCEPTION 'Approved governance revisions are immutable';
      END IF;
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Governance revisions cannot be deleted';
      END IF;
      trusted_subject := current_setting('lrm.actor_id', true);
      SELECT role INTO role_name FROM lrm_principal
        WHERE subject = trusted_subject AND enabled;
      IF TG_OP = 'INSERT' THEN
        IF role_name IS DISTINCT FROM 'MAKER'
           OR NEW.maker_id IS DISTINCT FROM trusted_subject
           OR NEW.status <> 'DRAFT_UNVERIFIED' THEN
          RAISE EXCEPTION 'Only authenticated maker may create a draft';
        END IF;
      ELSIF OLD.status = 'DRAFT_UNVERIFIED' AND NEW.status = 'PENDING' THEN
        IF role_name IS DISTINCT FROM 'MAKER'
           OR NEW.maker_id IS DISTINCT FROM trusted_subject THEN
          RAISE EXCEPTION 'Only original maker may submit draft';
        END IF;
      ELSIF OLD.status = 'PENDING' AND NEW.status = 'DRAFT_UNVERIFIED' THEN
        IF role_name IS DISTINCT FROM 'CHECKER' OR NEW.rejected_by_id
           IS DISTINCT FROM trusted_subject OR NEW.rejection_reason IS NULL THEN
          RAISE EXCEPTION 'Independent checker rejection evidence required';
        END IF;
      ELSIF OLD.status = 'PENDING' AND NEW.status IN ('ACTIVE','RETIRED') THEN
        IF role_name IS DISTINCT FROM 'CHECKER'
           OR NEW.checker_id IS DISTINCT FROM trusted_subject
           OR NEW.checker_id = NEW.maker_id THEN
          RAISE EXCEPTION 'Independent checker approval required';
        END IF;
        PERFORM pg_advisory_xact_lock(hashtextextended(NEW.kind || ':' || NEW.item_key, 0));
        SELECT max(effective_from) INTO max_approved_from
           FROM lrm_governed_revision WHERE kind = NEW.kind AND item_key = NEW.item_key
               AND status IN ('ACTIVE','RETIRED');
        IF max_approved_from IS NOT NULL AND NEW.effective_from <= max_approved_from THEN
          RAISE EXCEPTION 'Backdated or same-day approval is prohibited';
        END IF;
        IF NEW.status = 'ACTIVE' AND NEW.kind = 'PARAMETER' AND (
             NEW.source_document_sha256 IS NULL
             OR NEW.source_document_sha256 !~ '^[a-f0-9]{64}$'
             OR nullif(btrim(NEW.verification_ref), '') IS NULL) THEN
          RAISE EXCEPTION 'Regulatory verification evidence missing';
        END IF;
        IF NEW.status = 'ACTIVE' AND NEW.kind = 'MAPPING' AND
             nullif(btrim(NEW.syariah_review_ref), '') IS NULL THEN
          RAISE EXCEPTION 'Sharia review reference missing';
        END IF;
        IF NEW.legal_basis ILIKE '%[VERIFY]%'
           OR NEW.legal_basis ILIKE '%TBD%' THEN
          RAISE EXCEPTION 'Unverified legal basis cannot be activated';
        END IF;
      ELSE
        RAISE EXCEPTION 'Unsupported governance state transition';
      END IF;
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    CREATE TRIGGER trg_lrm_revision_guard BEFORE INSERT OR UPDATE OR DELETE
       ON lrm_governed_revision FOR EACH ROW
       EXECUTE FUNCTION lrm_enforce_revision_guard();
    """)


def downgrade() -> None:
    op.execute('DROP TRIGGER IF EXISTS trg_lrm_revision_guard ON lrm_governed_revision')
    op.execute('DROP FUNCTION IF EXISTS lrm_enforce_revision_guard()')
    op.drop_index('uq_approved_same_date', table_name='lrm_governed_revision')
    op.drop_index('ix_rev_effective_lookup', table_name='lrm_governed_revision')
    op.drop_table('lrm_governed_revision')
    op.drop_table('lrm_principal')
