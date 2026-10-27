"""Approved card spend per day, in silver; optionally as of a version."""
import sys

from globalbank.session import get_spark

SILVER = 'globalbank_dev.silver.card_transactions'

spark = get_spark()
version = f' VERSION AS OF {sys.argv[1]}' if len(sys.argv) > 1 else ''
for r in spark.sql(f"""SELECT to_date(auth_ts) AS day, count(*) AS auths,
                              sum(amount) AS spend
                       FROM {SILVER}{version}
                       WHERE status = 'APPROVED' AND currency = 'EUR'
                       GROUP BY day ORDER BY day""").collect():
    print(f'{r.day}  {r.auths:>6,} auths  {r.spend:>12,.2f} EUR')
