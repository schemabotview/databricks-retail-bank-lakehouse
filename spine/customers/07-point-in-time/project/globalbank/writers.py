"""Two writers, one table: post two days at the same moment."""
import sys
from concurrent.futures import ThreadPoolExecutor

from globalbank.ledger import SILVER, create, post
from globalbank.session import get_spark

spark = get_spark()
create(spark)
with ThreadPoolExecutor(max_workers=2) as pool:
    done = pool.map(lambda day: post(spark, day), sys.argv[1:])
    list(done)  # raises here if either writer failed
for day in sys.argv[1:]:
    print(f'{day}: committed')
print(f'{SILVER}: {spark.table(SILVER).count():,} rows')
