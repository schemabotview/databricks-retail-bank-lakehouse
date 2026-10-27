-- Gold, as the business reads it: approved card spend per day, in EUR.
SELECT day, auths, spend
FROM globalbank_dev.gold.card_spend_daily
ORDER BY day
