"""Ask the workspace who we are, then run a first Spark job there."""
from globalbank.session import get_spark

spark = get_spark()
who = spark.sql('SELECT current_user() AS me, current_catalog() AS cat').first()
print(f'Spark {spark.version} on serverless')
print(f'as {who.me}, in catalog {who.cat}')
spark.range(3).show()
