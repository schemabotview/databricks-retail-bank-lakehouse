-- Gold: the account facts consumers group and filter by, one row per account.
CREATE OR REPLACE TABLE globalbank_dev.gold.accounts AS
SELECT a.account_id, a.product, a.overdraft_limit, c.region, c.segment
FROM globalbank_dev.silver.accounts a
JOIN globalbank_dev.silver.customers c USING (customer_id);

SELECT count(*) AS accounts, count_if(product = 'current') AS current,
       count(DISTINCT region) AS regions, count(DISTINCT segment) AS segments
FROM globalbank_dev.gold.accounts
