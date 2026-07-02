"""
Cross-account Redshift query execution via Data API.
No database credentials — IAM role chain handles auth.
"""
import boto3
import json
import time

CROSS_ACCOUNT_ROLE = 'arn:aws:iam::XXXXXXXXXXXX:role/redshift_query_role'
CLUSTER = 'analytics-cluster'
DATABASE = 'analytics'
REGION = 'us-east-1'

DEFAULT_SQL = "SELECT current_date AS today, current_user AS user_name"


def lambda_handler(event, context):
    sql = event.get('sql', DEFAULT_SQL)

    # assume cross-account role
    sts = boto3.client('sts', region_name=REGION)
    assumed = sts.assume_role(
        RoleArn=CROSS_ACCOUNT_ROLE,
        RoleSessionName='LambdaRedshiftQuery'
    )
    creds = assumed['Credentials']

    # execute via Data API (no connection management, no psycopg2)
    rs = boto3.client(
        'redshift-data',
        region_name=REGION,
        aws_access_key_id=creds['AccessKeyId'],
        aws_secret_access_key=creds['SecretAccessKey'],
        aws_session_token=creds['SessionToken'],
    )

    resp = rs.execute_statement(ClusterIdentifier=CLUSTER, Database=DATABASE, Sql=sql)
    query_id = resp['Id']

    # poll until done (Data API is async)
    for _ in range(120):
        status = rs.describe_statement(Id=query_id)
        if status['Status'] == 'FINISHED':
            result = rs.get_statement_result(Id=query_id)
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'sql': sql,
                    'rowCount': result['TotalNumRows'],
                    'columns': [col['name'] for col in result.get('ColumnMetadata', [])],
                    'records': result['Records'][:20],
                })
            }
        elif status['Status'] in ('FAILED', 'ABORTED'):
            return {
                'statusCode': 500,
                'body': json.dumps({'error': status.get('Error', 'Unknown'), 'sql': sql})
            }
        time.sleep(1)

    return {'statusCode': 408, 'body': json.dumps({'error': 'Timeout', 'sql': sql})}
