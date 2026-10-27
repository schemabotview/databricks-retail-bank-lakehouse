-- Gold: what the bank reports on its card book, for the last days of October.
CREATE OR REPLACE TABLE globalbank_dev.gold.regulatory_snapshot AS
SELECT to_date(t.auth_ts) AS day, count(*) AS approved,
       count(s.auth_id) AS cleared, sum(s.amount_eur) AS cleared_eur
FROM globalbank_dev.silver.card_transactions t
LEFT JOIN globalbank_dev.silver.settlements s USING (auth_id)
WHERE t.status = 'APPROVED'
GROUP BY ALL;

SELECT count(*) AS days, sum(approved) AS approved FROM
globalbank_dev.gold.regulatory_snapshot
