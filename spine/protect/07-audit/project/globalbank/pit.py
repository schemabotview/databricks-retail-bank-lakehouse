"""A payment joined to its customer's KYC status then, and now."""
from globalbank.session import get_spark

spark = get_spark()
spark.sql("""
    SELECT a.auth_id, a.auth_ts, c.customer_id
    FROM globalbank_dev.bronze.card_auths a
    JOIN globalbank_dev.silver.accounts c
      ON a.card_id = 'K' || substr(c.account_id, 2, 6)
     AND c.product = 'current'""").createOrReplaceTempView('paid')
both = spark.sql("""
    SELECT p.auth_id, p.auth_ts, p.customer_id,
           h.kyc_status AS kyc_then, now.kyc_status AS kyc_now
    FROM paid p
    JOIN globalbank_dev.silver.customers now USING (customer_id)
    JOIN globalbank_dev.silver.customers_history h
      ON h.customer_id = p.customer_id
     AND p.auth_ts >= h.valid_from
     AND (p.auth_ts < h.valid_to OR h.valid_to IS NULL)""")
differ = both.where('kyc_then != kyc_now')
print(f'{both.count():,} payments;'
      f' {differ.count():,} with another KYC status then')
differ.orderBy('auth_ts').show(5, truncate=False)
