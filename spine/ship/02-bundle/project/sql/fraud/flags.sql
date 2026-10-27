-- Gold: card-testing flags, by the velocity rule (Course 9).
CREATE OR REPLACE TABLE globalbank_dev.gold.fraud_flags AS
SELECT auth_id, card_id, auth_ts, auths_10m
FROM (SELECT auth_id, card_id, auth_ts,
             count(*) OVER (PARTITION BY card_id ORDER BY auth_ts
                            RANGE BETWEEN INTERVAL 10 MINUTES PRECEDING
                                      AND CURRENT ROW) AS auths_10m
      FROM globalbank_dev.silver.card_transactions)
WHERE auths_10m > 5
