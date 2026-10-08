# Runbook: when an alarm fires

The stack (`template.yaml`) sends three CloudWatch alarms and one budget warning to the SNS topic
`ground-truth-alerts`, which emails the address passed as `AlertEmail` (`make stack ALERT_EMAIL=...`).
The subscription has to be confirmed once from the email AWS sends.

| Alarm | Means | Do |
|---|---|---|
| `ground-truth-lambda-errors` | The ingest Lambda crashed in 2 hours in a row. | Read the last log line (below). A crash is a bug: fix it, `make deploy`, then `make run`. |
| `ground-truth-ingest-run-error` | Two runs in a row stopped early: the OpenAQ key was rejected (401/403), or the API was unreachable 5 stations in a row. The run still publishes what it can. | A 401: put the right key in SSM (`aws ssm put-parameter --name /ground-truth/openaq-key --type SecureString --overwrite --value <key> --profile groundtruth`), then `make run`. Unreachable: wait an hour; if it stays, check https://api.openaq.org/v3/locations/8235 by hand. |
| `ground-truth-stale-data` | `data_through` is more than 3 hours behind now, or no run has reported for an hour at all. | `make run` and read its summary. `"published": false` with a `reason` says why the hour wasn't published (fewer than half the stations have a recent reading, most often OpenAQ itself running late). If `reason` names the key, see the row above. If the Lambda isn't being invoked, check the EventBridge rule is enabled. |
| `ground-truth-monthly` (budget) | The project tag has spent 80% of $5 this month. | Read Cost Explorer filtered by `project=ground-truth`. The hourly runs cost cents; anything else is a surprise. |

## The last log line

Every run prints one JSON line. The useful keys: `error` (why it stopped early), `published` and `reason`,
`data_through`, `overlap_ratio` (API against archive on shared hours; about 1.0 is right), `api_calls`,
`statuses` (how many ok/watch/flag/nodata), and `metrics` (what was sent to CloudWatch).

```
aws logs tail /aws/lambda/$(aws cloudformation describe-stacks --stack-name ground-truth \
  --query "Stacks[0].Outputs[?OutputKey=='IngestFunctionName'].OutputValue" --output text \
  --profile groundtruth) --since 3h --profile groundtruth | grep '{"new_hours"'
```

## Metrics the Lambda publishes (namespace `GroundTruth`, dimension `Stack`)

- `DataAgeHours`: hours from the end of the newest scored hour to now. Normal is 1 to 2 (OpenAQ publishes an hour a little after it ends).
- `IngestErrors`: 1 when the run stopped early, else 0.

## Testing the alarms

Put a wrong key in SSM, wait for two hourly runs (or `make run` twice an hour apart): `ground-truth-ingest-run-error`
goes to ALARM and sends the email; put the real key back and the next run sends the OK email.
