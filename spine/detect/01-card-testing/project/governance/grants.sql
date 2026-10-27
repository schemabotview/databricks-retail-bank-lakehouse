-- Who reads which layer. The principals are ACCOUNT groups, synced from
-- the bank's identity provider: engineers build, risk investigates,
-- finance and branches read only the finished products in gold.
GRANT USE CATALOG ON CATALOG globalbank_dev TO `engineers`;
GRANT USE SCHEMA, SELECT ON SCHEMA globalbank_dev.bronze TO `engineers`;
GRANT USE SCHEMA, SELECT ON SCHEMA globalbank_dev.silver TO `engineers`;
GRANT USE SCHEMA, SELECT ON SCHEMA globalbank_dev.silver TO `risk`;
GRANT USE SCHEMA, SELECT ON SCHEMA globalbank_dev.gold TO `finance`;
GRANT USE SCHEMA, SELECT ON SCHEMA globalbank_dev.gold TO `branches`;
