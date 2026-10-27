-- Classify every column that identifies a person, so it can be found.
ALTER TABLE globalbank_dev.silver.customers
  ALTER COLUMN national_id SET TAGS ('pii' = 'national_id');
ALTER TABLE globalbank_dev.silver.customers
  ALTER COLUMN first_name SET TAGS ('pii' = 'name');
ALTER TABLE globalbank_dev.silver.customers
  ALTER COLUMN last_name SET TAGS ('pii' = 'name');
ALTER TABLE globalbank_dev.silver.customers
  ALTER COLUMN date_of_birth SET TAGS ('pii' = 'birth_date');
ALTER TABLE globalbank_dev.silver.customers
  ALTER COLUMN email SET TAGS ('pii' = 'contact');
ALTER TABLE globalbank_dev.silver.customers
  ALTER COLUMN address SET TAGS ('pii' = 'contact');
ALTER TABLE globalbank_dev.silver.accounts
  ALTER COLUMN iban SET TAGS ('pii' = 'account_number');
