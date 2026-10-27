-- One account's October, a week to a row: the balance each evening.
SELECT min(day) AS week_from,
       array_join(transform(array_sort(collect_list(struct(day, balance))),
                            x -> format_number(x.balance, 0)), '  ') AS balances
FROM globalbank_dev.gold.daily_balances
WHERE account_id = :account AND day >= DATE'2026-10-01'
GROUP BY weekofyear(day)
ORDER BY week_from
