# redshift-lambda

Lambda function that assumes a cross-account IAM role via STS, then executes SQL against a Redshift cluster using the Data API. Deploy script included.

I use this as a test harness — validate queries against production data before wiring them into a pipeline. Also proves out the cross-account pattern for anyone who needs to run Redshift queries from a different AWS account without managing database credentials.

## how it works

1. Lambda receives `{"sql": "SELECT ..."}` (or runs default connectivity test)
2. Assumes cross-account role via STS
3. Calls `redshift-data:ExecuteStatement` with temporary credentials
4. Polls `DescribeStatement` until FINISHED/FAILED
5. Returns results (first 20 rows)

No database password anywhere. The cross-account role grants execute permissions — Lambda's execution role grants assume-role permission. Clean IAM chain.
