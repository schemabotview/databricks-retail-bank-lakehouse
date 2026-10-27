"""Silver, reconciled: every bronze row is kept, resent or quarantined."""
from globalbank.session import get_spark

spark = get_spark()
n = lambda sql: spark.sql(sql).first()[0]
bronze = n('SELECT count(*) FROM globalbank_dev.bronze.card_auths')
silver = n('SELECT count(*) FROM globalbank_dev.silver.card_transactions')
held = n('SELECT count(*) FROM'
         ' globalbank_dev.silver.card_transactions_quarantine')
resent = n("""SELECT count(*) - count(DISTINCT auth_id)
              FROM globalbank_dev.bronze.card_auths""")
print(f'bronze      {bronze:>7,}')
print(f'silver      {silver:>7,}')
print(f'quarantine  {held:>7,}')
print(f'resends     {resent:>7,}')
print(f'{silver:,} + {held:,} + {resent:,} = {silver + held + resent:,}'
      f" {'=' if silver + held + resent == bronze else '!='} {bronze:,}")
