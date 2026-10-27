-- Card testing, as a rule: more than 5 authorizations on one card within
-- 10 minutes. Illustrative threshold, not a real fraud policy.
WITH velocity AS (
  SELECT auth_id, card_id, auth_ts,
         count(*) OVER (PARTITION BY card_id ORDER BY auth_ts
                        RANGE BETWEEN INTERVAL 10 MINUTES PRECEDING
                                  AND CURRENT ROW) AS auths_10m
  FROM globalbank_dev.silver.card_transactions)
SELECT to_date(v.auth_ts) AS day,
       count_if(v.auths_10m > 5) AS flagged,
       count_if(v.auths_10m > 5 AND c.auth_id IS NOT NULL) AS fraud_flagged,
       count(c.auth_id) AS fraud
FROM velocity v
LEFT JOIN globalbank_dev.silver.chargebacks c USING (auth_id)
GROUP BY ALL ORDER BY day
