-- Accounts below their overdraft limit at the end of a day: an alert's query.
SELECT b.day, count(*) AS accounts, round(min(b.balance)) AS lowest_eur
FROM globalbank_dev.gold.daily_balances b
JOIN globalbank_dev.gold.accounts a USING (account_id)
WHERE b.balance < -a.overdraft_limit AND b.day >= DATE'2026-10-25'
GROUP BY ALL ORDER BY b.day
