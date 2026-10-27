-- A branch manager sees their region's customers, and risk every region.
CREATE OR REPLACE FUNCTION globalbank_dev.governance.my_region(
  row_region STRING)
RETURNS BOOLEAN
RETURN EXISTS(SELECT 1 FROM globalbank_dev.governance.roles r
              WHERE r.user_name = current_user()
                AND (r.role = 'risk' OR r.region = row_region));

ALTER TABLE globalbank_dev.silver.customers
  SET ROW FILTER globalbank_dev.governance.my_region ON (region);
