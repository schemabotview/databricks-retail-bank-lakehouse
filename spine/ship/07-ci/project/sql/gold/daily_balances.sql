-- Gold: every account's balance at the end of every day, in EUR.
-- Opening balance + the core system's postings - what cards cleared.
CREATE OR REPLACE TABLE globalbank_dev.gold.daily_balances AS
WITH days AS (
  SELECT explode(sequence(DATE'2026-09-01', DATE'2026-10-31')) AS day),
moves AS (
  SELECT account_id, posted_date AS day, amount
  FROM globalbank_dev.silver.postings
  UNION ALL
  SELECT a.account_id, s.cleared_date, -s.amount_eur
  FROM globalbank_dev.silver.settlements s
  JOIN globalbank_dev.silver.accounts a
    ON s.card_id = 'K' || substr(a.account_id, 2, 6)
   AND a.product = 'current'),
daily AS (SELECT account_id, day, sum(amount) AS moved
          FROM moves GROUP BY ALL)
SELECT a.account_id, d.day,
       a.opening_balance + sum(coalesce(m.moved, 0)) OVER (
         PARTITION BY a.account_id ORDER BY d.day) AS balance
FROM globalbank_dev.silver.accounts a
JOIN days d ON d.day >= a.opened
LEFT JOIN daily m ON m.account_id = a.account_id AND m.day = d.day
