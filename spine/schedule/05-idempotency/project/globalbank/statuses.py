"""Silver's authorizations by status, with what cleared in euros."""
from globalbank.session import get_spark

SILVER = 'globalbank_dev.silver.card_transactions'

spark = get_spark()
rows = spark.sql(f"""SELECT status, count(*) AS auths,
                            sum(settled_eur) AS settled_eur
                     FROM {SILVER} GROUP BY status ORDER BY status""")
for r in rows.collect():
    cleared = '' if r.settled_eur is None else f'{r.settled_eur:>13,.2f} EUR'
    print(f'{r.status:<10}{r.auths:>7,} auths  {cleared}')
