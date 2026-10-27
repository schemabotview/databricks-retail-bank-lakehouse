-- One account's October statement, a line per entry.
SELECT stack(7,
         'opening balance', CAST(opening AS DECIMAL(18,2)),
         'card payments', CAST(-cards AS DECIMAL(18,2)),
         'salary', CAST(salary AS DECIMAL(18,2)),
         'rent', CAST(rent AS DECIMAL(18,2)),
         'transfers', CAST(transfers AS DECIMAL(18,2)),
         'closing balance', CAST(closing AS DECIMAL(18,2)),
         'check', CAST(opening - cards + salary + rent + transfers - closing
                       AS DECIMAL(18,2))) AS (line, eur)
FROM globalbank_dev.gold.monthly_statements
WHERE account_id = :account
