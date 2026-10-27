-- Gold: every account's October statement.
CREATE OR REPLACE TABLE globalbank_dev.gold.monthly_statements AS
WITH card AS (
  SELECT a.account_id, sum(s.amount_eur) AS cards, count(*) AS card_lines
  FROM globalbank_dev.silver.settlements s
  JOIN globalbank_dev.silver.accounts a
    ON s.card_id = 'K' || substr(a.account_id, 2, 6)
   AND a.product = 'current'
  WHERE s.cleared_date BETWEEN DATE'2026-10-01' AND DATE'2026-10-31'
    AND s.kind = 'SETTLEMENT'
  GROUP BY ALL),
core AS (
  SELECT account_id,
         sum(amount) FILTER (WHERE kind = 'SALARY') AS salary,
         sum(amount) FILTER (WHERE kind = 'RENT') AS rent,
         sum(amount) FILTER (WHERE kind = 'TRANSFER') AS transfers
  FROM globalbank_dev.silver.postings
  WHERE posted_date BETWEEN DATE'2026-10-01' AND DATE'2026-10-31'
  GROUP BY ALL)
SELECT '2026-10' AS month, b.account_id,
       o.balance AS opening, coalesce(card.cards, 0) AS cards,
       coalesce(card.card_lines, 0) AS card_lines,
       coalesce(core.salary, 0) AS salary, coalesce(core.rent, 0) AS rent,
       coalesce(core.transfers, 0) AS transfers, b.balance AS closing
FROM globalbank_dev.gold.daily_balances b
JOIN globalbank_dev.gold.daily_balances o
  ON o.account_id = b.account_id AND o.day = DATE'2026-09-30'
LEFT JOIN card ON card.account_id = b.account_id
LEFT JOIN core ON core.account_id = b.account_id
WHERE b.day = DATE'2026-10-31';

SELECT count(*) AS statements, round(avg(closing)) AS avg_closing,
       count_if(closing < 0) AS overdrawn
FROM globalbank_dev.gold.monthly_statements
