-- Gold: the month-end figures the ledger closes on, appended per run.
CREATE TABLE IF NOT EXISTS globalbank_dev.gold.month_end
  (month STRING, accounts BIGINT, deposits_eur DECIMAL(18,2));
INSERT INTO globalbank_dev.gold.month_end
SELECT month, count(*), sum(closing)
FROM globalbank_dev.gold.monthly_statements GROUP BY month
