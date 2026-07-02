"""
Lambda handler: EventBridge triggers this hourly.
Polls configured carriers, normalizes, upserts to RDS.
"""
import json
import os
import boto3
from datetime import datetime

SECRETS_ARN = os.environ['CARRIER_SECRETS_ARN']
DB_SECRET_ARN = os.environ['DB_SECRET_ARN']


def get_secret(arn):
    client = boto3.client('secretsmanager')
    resp = client.get_secret_value(SecretId=arn)
    return json.loads(resp['SecretString'])


def lambda_handler(event, context):
    carrier_creds = get_secret(SECRETS_ARN)
    db_creds = get_secret(DB_SECRET_ARN)

    results = []
    for carrier_code, creds in carrier_creds.items():
        try:
            raw = poll_carrier(carrier_code, creds)
            normalized = normalize(carrier_code, raw)
            count = upsert(db_creds, normalized)
            results.append({'carrier': carrier_code, 'rows': count, 'status': 'ok'})
        except Exception as e:
            results.append({'carrier': carrier_code, 'error': str(e), 'status': 'failed'})

    return {
        'statusCode': 200,
        'body': json.dumps({
            'timestamp': datetime.utcnow().isoformat(),
            'results': results
        })
    }


def poll_carrier(carrier_code, creds):
    """Hit carrier REST endpoint with their auth. Validate response shape."""
    import requests
    url = creds['endpoint']
    headers = {'Authorization': f"Bearer {creds['token']}"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        raise ValueError(f"{carrier_code}: expected list, got {type(data).__name__}")
    return data


def normalize(carrier_code, raw_records):
    """Dispatch to carrier-specific normalizer."""
    from normalizers import DISPATCH
    normalizer = DISPATCH[carrier_code]
    return [normalizer(r) for r in raw_records]


def upsert(db_creds, records):
    """Idempotent upsert to shipments table."""
    import psycopg2
    conn = psycopg2.connect(
        host=db_creds['host'], port=db_creds['port'],
        dbname=db_creds['dbname'], user=db_creds['username'],
        password=db_creds['password'], sslmode='require'
    )
    cursor = conn.cursor()
    for r in records:
        cursor.execute("""
            INSERT INTO shipments (shipment_id, carrier, origin, destination, status, eta, updated_at)
            VALUES (%(shipment_id)s, %(carrier)s, %(origin)s, %(destination)s, %(status)s, %(eta)s, NOW())
            ON CONFLICT (shipment_id) DO UPDATE SET
                status = EXCLUDED.status, eta = EXCLUDED.eta, updated_at = NOW()
        """, r)
    conn.commit()
    cursor.close()
    conn.close()
    return len(records)
