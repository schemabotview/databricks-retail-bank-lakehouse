-- Gold: the month-end figures the ledger closes on: one row per month,
-- however many times the task runs.
CREATE TABLE IF NOT EXISTS globalbank_dev.gold.month_end
  (month STRING, accounts BIGINT, deposits_eur DECIMAL(18,2));
INSERT INTO globalbank_dev.gold.month_end REPLACE WHERE month = :month
SELECT month, count(*), sum(closing)
FROM globalbank_dev.gold.monthly_statements WHERE month = :month
GROUP BY month
