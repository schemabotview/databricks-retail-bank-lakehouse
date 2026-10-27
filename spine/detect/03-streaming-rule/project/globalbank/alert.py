"""Create the overdraft alert: the warehouse runs its query on a schedule."""
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service import sql

from globalbank.warehouse import warehouse

NAME = 'globalbank overdrafts'

w = WorkspaceClient()
query = Path('sql/alerts/overdrawn.sql').read_text()
alert = sql.AlertV2(
    display_name=NAME, query_text=query, warehouse_id=warehouse(w).id,
    evaluation=sql.AlertV2Evaluation(
        source=sql.AlertV2OperandColumn(name='accounts',
                                        aggregation=sql.Aggregation.SUM),
        comparison_operator=sql.ComparisonOperator.GREATER_THAN,
        threshold=sql.AlertV2Operand(
            value=sql.AlertV2OperandValue(double_value=0)),
        empty_result_state=sql.AlertEvaluationState.OK),
    schedule=sql.CronSchedule(quartz_cron_schedule='0 0 7 * * ?',
                              timezone_id='Europe/Amsterdam'))
for old in w.alerts_v2.list_alerts():
    if old.display_name == NAME:
        w.alerts_v2.trash_alert(old.id)
created = w.alerts_v2.create_alert(alert)
e = created.evaluation
print(f'{NAME}: created, {created.lifecycle_state.value.lower()}')
print(f'  when SUM(accounts) {e.comparison_operator.value} 0,'
      f' every day at 07:00 Europe/Amsterdam')
