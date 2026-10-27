"""Two writers, one table: post two days at the same moment."""
import re
import sys
from concurrent.futures import ThreadPoolExecutor

from globalbank.ledger import SILVER, create, post
from globalbank.session import get_spark


def post_until_committed(day):
    """Post a day; if another writer committed first, read again and retry."""
    for attempt in range(1, 4):
        try:
            post(spark, day)
            return f'{day}: committed on attempt {attempt}'
        except Exception as e:
            conflict = re.search(r'\[(DELTA_CONCURRENT\w*)', str(e))
            if not conflict:
                raise
            print(f'{day}: {conflict.group(1)}, retrying')


spark = get_spark()
create(spark)
with ThreadPoolExecutor(max_workers=2) as pool:
    for line in pool.map(post_until_committed, sys.argv[1:]):
        print(line)
print(f'{SILVER}: {spark.table(SILVER).count():,} rows')
