-- Card spend on one day: the filter the regulator's report runs most.
SELECT count(*) AS settlements, sum(amount_eur) AS eur
FROM globalbank_dev.silver.settlements
WHERE cleared_date = DATE'2026-10-30'
