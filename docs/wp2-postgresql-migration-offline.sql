BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_wp2

CREATE TABLE lrm_principal (
    subject VARCHAR(180) NOT NULL, 
    role VARCHAR(24) NOT NULL, 
    enabled BOOLEAN NOT NULL, 
    PRIMARY KEY (subject), 
    CONSTRAINT ck_principal_role CHECK (role in ('MAKER','CHECKER','AUDITOR','ADMINISTRATOR','ALCO'))
);

CREATE TABLE lrm_governed_revision (
    id VARCHAR(36) NOT NULL, 
    kind VARCHAR(20) NOT NULL, 
    item_key VARCHAR(260) NOT NULL, 
    version INTEGER NOT NULL, 
    status VARCHAR(25) NOT NULL, 
    effective_from DATE NOT NULL, 
    effective_to DATE, 
    payload_json TEXT NOT NULL, 
    legal_basis TEXT NOT NULL, 
    change_reason TEXT NOT NULL, 
    retirement BOOLEAN NOT NULL, 
    maker_id VARCHAR(180) NOT NULL, 
    checker_id VARCHAR(180), 
    rejected_by_id VARCHAR(180), 
    source_document_sha256 VARCHAR(64), 
    verification_ref TEXT, 
    syariah_review_ref TEXT, 
    submitted_at TIMESTAMP WITH TIME ZONE, 
    approved_at TIMESTAMP WITH TIME ZONE, 
    rejected_at TIMESTAMP WITH TIME ZONE, 
    rejection_reason TEXT, 
    created_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_revision_version UNIQUE (kind, item_key, version), 
    CONSTRAINT ck_revision_kind CHECK (kind IN ('PARAMETER','MAPPING')), 
    CONSTRAINT ck_revision_status CHECK (status IN ('DRAFT_UNVERIFIED','PENDING','ACTIVE','RETIRED')), 
    CONSTRAINT ck_revision_dates CHECK (effective_to IS NULL OR effective_to >= effective_from), 
    CONSTRAINT ck_revision_four_eyes CHECK (checker_id IS NULL OR checker_id <> maker_id), 
    CONSTRAINT ck_revision_approval_fields CHECK (status NOT IN ('ACTIVE','RETIRED') OR (checker_id IS NOT NULL AND approved_at IS NOT NULL AND submitted_at IS NOT NULL)), 
    CONSTRAINT ck_revision_active_nonretirement CHECK (status <> 'ACTIVE' OR retirement = false), 
    CONSTRAINT ck_revision_retired_tombstone CHECK (status <> 'RETIRED' OR retirement = true), 
    CONSTRAINT ck_parameter_verified CHECK (status <> 'ACTIVE' OR kind <> 'PARAMETER' OR (source_document_sha256 IS NOT NULL AND verification_ref IS NOT NULL)), 
    CONSTRAINT ck_mapping_sharia_review CHECK (status <> 'ACTIVE' OR kind <> 'MAPPING' OR syariah_review_ref IS NOT NULL), 
    FOREIGN KEY(maker_id) REFERENCES lrm_principal (subject), 
    FOREIGN KEY(checker_id) REFERENCES lrm_principal (subject), 
    FOREIGN KEY(rejected_by_id) REFERENCES lrm_principal (subject)
);

CREATE INDEX ix_rev_effective_lookup ON lrm_governed_revision (kind, item_key, effective_from);

CREATE UNIQUE INDEX uq_approved_same_date ON lrm_governed_revision (kind, item_key, effective_from) WHERE status IN ('ACTIVE','RETIRED');

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
        IF NEW.legal_basis ILIKE '%%[VERIFY]%%'
           OR NEW.legal_basis ILIKE '%%TBD%%' THEN
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
       EXECUTE FUNCTION lrm_enforce_revision_guard();;

INSERT INTO alembic_version (version_num) VALUES ('0001_wp2') RETURNING alembic_version.version_num;

COMMIT;

