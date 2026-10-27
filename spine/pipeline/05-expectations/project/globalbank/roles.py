"""Say which role the current user reads as: their row in governance.roles."""
import sys

from globalbank.session import get_spark

ROLES = 'globalbank_dev.governance.roles'

role = sys.argv[1]
region = sys.argv[2] if len(sys.argv) > 2 else None
spark = get_spark()
spark.sql(f'DELETE FROM {ROLES} WHERE user_name = current_user()')
spark.sql(f'INSERT INTO {ROLES} VALUES (current_user(), :role, :region)',
          args={'role': role, 'region': region})
me = spark.sql('SELECT current_user()').first()[0]
print(f'{me} reads as {role}' + (f', {region}' if region else ''))
