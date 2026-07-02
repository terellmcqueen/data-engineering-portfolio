"""
Main orchestrator: creds → fetch → S3 → consolidate → enrich → QA
Each step logs what it did. Skippable via CLI flags. Idempotent.
"""
import argparse
import logging
import sys
import time
from datetime import date
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.yaml"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def check_credentials(config):
    import subprocess
    result = subprocess.run(
        ["ada", "credentials", "print", f"--profile={config['redshift']['profile']}"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        logger.error("Credentials expired. Refresh: ada credentials update --profile=%s",
                     config['redshift']['profile'])
        sys.exit(1)


def run_consolidation(config, skip=False):
    if skip:
        logger.info("Skipping consolidation (--skip-consolidator)")
        return 0
    from consolidator import CarrierConsolidator
    consolidator = CarrierConsolidator(config['carriers'], config['redshift'])
    rows = consolidator.run()
    logger.info("Consolidation: %d rows inserted", rows)
    return rows


def run_enrichment(config, skip=False):
    if skip:
        logger.info("Skipping enrichment (--skip-enrichment)")
        return
    from db_utils import get_connection
    sql_file = ROOT / "enrich.sql"
    statements = [s.strip() for s in sql_file.read_text().split(';') if s.strip()]
    conn = get_connection(config['redshift'])
    cursor = conn.cursor()
    for i, stmt in enumerate(statements, 1):
        start = time.time()
        cursor.execute(stmt)
        conn.commit()
        logger.info("Enrichment %d/%d (%.1fs)", i, len(statements), time.time() - start)
    cursor.close()
    conn.close()


def run_quality_checks(config):
    from db_utils import get_connection
    conn = get_connection(config['redshift'])
    cursor = conn.cursor()
    cursor.execute("""
        SELECT carrier_code, COUNT(*),
               SUM(CASE WHEN destination_facility IS NULL THEN 1 ELSE 0 END) AS blanks
        FROM analytics.carrier_dwell_enriched
        WHERE load_date = CURRENT_DATE GROUP BY 1
    """)
    alerts = []
    for carrier, total, blanks in cursor.fetchall():
        threshold = config['carriers'].get(carrier, {}).get('blank_threshold', 50)
        if blanks > threshold:
            alerts.append(f"{carrier}: {blanks} blanks (threshold: {threshold})")
    cursor.close()
    conn.close()
    if alerts:
        logger.warning("Quality alerts:\n  %s", "\n  ".join(alerts))
    return alerts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--skip-consolidator", action="store_true")
    parser.add_argument("--skip-enrichment", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    config = load_config()

    check_credentials(config)
    run_consolidation(config, skip=args.skip_consolidator)
    run_enrichment(config, skip=args.skip_enrichment)
    alerts = run_quality_checks(config)

    logger.info("Done — %s", date.today())
    if alerts:
        sys.exit(1)


if __name__ == "__main__":
    main()
