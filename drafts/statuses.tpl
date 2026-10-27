"""Silver's authorizations by status, with what cleared in euros."""
from globalbank.session import get_spark

SILVER = 'globalbank_dev.silver.card_transactions'

spark = get_spark()
spark.sql(f"""SELECT status, count(*) AS auths,
                     sum(settled_eur) AS settled_eur
              FROM {SILVER} GROUP BY status ORDER BY status""").show()
