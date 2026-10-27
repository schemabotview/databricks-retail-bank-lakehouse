-- Who reads as which role: one row per user, read by every mask and filter.
CREATE TABLE IF NOT EXISTS globalbank_dev.governance.roles
  (user_name STRING, role STRING, region STRING);

-- National IDs and IBANs: only risk sees them whole.
CREATE OR REPLACE FUNCTION globalbank_dev.governance.unless_risk(v STRING)
RETURNS STRING
RETURN IF(EXISTS(SELECT 1 FROM globalbank_dev.governance.roles r
                 WHERE r.user_name = current_user() AND r.role = 'risk'),
          v, concat('*****', right(v, 3)));

ALTER TABLE globalbank_dev.silver.customers
  ALTER COLUMN national_id SET MASK globalbank_dev.governance.unless_risk;
ALTER TABLE globalbank_dev.silver.accounts
  ALTER COLUMN iban SET MASK globalbank_dev.governance.unless_risk;
