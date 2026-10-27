-- One account's October statement, a line per entry.
SELECT stack(7, 'opening balance', opening, 'card payments', -cards,
             'salary', salary, 'rent', rent, 'transfers', transfers,
             'closing balance', closing,
             'check', opening - cards + salary + rent + transfers - closing)
       AS (line, eur)
FROM globalbank_dev.gold.monthly_statements
WHERE account_id = :account
