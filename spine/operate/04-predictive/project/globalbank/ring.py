"""Card testing: many authorizations on one card in a few minutes, overnight."""
import sys

from globalbank.session import get_spark

day = sys.argv[1]
spark = get_spark()
cards = spark.sql(f"""
    SELECT card_id, count(*) AS auths, sum(amount) AS total,
           count_if(status = 'DECLINED') AS declined,
           count(DISTINCT merchant_id) AS merchants,
           min(auth_ts) AS first, max(auth_ts) AS last
    FROM globalbank_dev.silver.card_transactions
    WHERE to_date(auth_ts) = '{day}' AND hour(auth_ts) < 5
    GROUP BY card_id HAVING count(*) > 3 ORDER BY first""").collect()
print(f'{day}, before 05:00: {len(cards)} cards with more than 3 auths')
for c in cards:
    span = (c.last - c.first).seconds // 60
    print(f'  {c.card_id}  {c.auths} auths in {span:>2} min  {c.total:>6} EUR'
          f'  {c.declined} declined  {c.merchants} merchants')
one = cards[0].card_id
times = spark.sql(f"""
    SELECT auth_ts, amount FROM globalbank_dev.silver.card_transactions
    WHERE card_id = '{one}' AND to_date(auth_ts) = '{day}'
      AND hour(auth_ts) < 5 ORDER BY auth_ts""").collect()
print(f'{one}:', ' '.join(f"{t.auth_ts:%H:%M}/{t.amount}" for t in times))
