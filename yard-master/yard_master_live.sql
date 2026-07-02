-- hourly ETL: 5 sources → 107-column live yard snapshot
-- pattern: CTAS staging → validate → truncate+insert production
-- production table is NEVER dropped

DROP TABLE IF EXISTS analytics.yard_master_live_stg;
CREATE TABLE analytics.yard_master_live_stg
DISTKEY(equipment_visit_id) SORTKEY(snapshot_date, facility_code) AS

WITH facility_dim AS (
    -- normalize facility metadata across two systems that disagree on naming
    SELECT COALESCE(s.node_code, q.facility_code) AS facility_code,
           COALESCE(s.node_group, q.facility_type) AS facility_type,
           COALESCE(q.facility_region, 'unassigned') AS region,
           COALESCE(s.scope, q.country) AS country
    FROM (SELECT node_code, node_group, scope,
                 ROW_NUMBER() OVER (PARTITION BY node_code ORDER BY snapshot_date DESC) AS rnk
          FROM reference.facility_nodes WHERE region_id = 1 AND scope IN ('US','CA')) s
    FULL OUTER JOIN (SELECT DISTINCT facility_code, facility_type, facility_region, country
                     FROM operations.appointments_hourly WHERE country IN ('US','CA')) q
        ON s.node_code = q.facility_code
    WHERE s.rnk = 1 OR s.rnk IS NULL
),

-- safe-cast: upstream changed types without notice. all VARCHAR first, regex validate, then convert.
appointments_raw AS (
    SELECT facility_code::VARCHAR AS facility_code,
           carrier_code::VARCHAR AS carrier_code,
           trailer_id::VARCHAR AS trailer_id,
           status::VARCHAR AS status,
           arrival_datetime::VARCHAR AS arrival_datetime_raw,
           appointment_id::VARCHAR AS appointment_id,
           unit_count::VARCHAR AS unit_count_raw,
           creation_datetime::VARCHAR AS creation_datetime_raw,
           record_version::VARCHAR AS record_version_raw
    FROM operations.inbound_appointments
),
appointments AS (
    SELECT facility_code, carrier_code, trailer_id, status,
           CASE WHEN arrival_datetime_raw != '' THEN arrival_datetime_raw::TIMESTAMP ELSE NULL END AS arrival_datetime,
           appointment_id,
           CASE WHEN REGEXP_COUNT(TRIM(unit_count_raw), '^-?[0-9]+$') = 1
                THEN TRIM(unit_count_raw)::INTEGER ELSE NULL END AS unit_count,
           CASE WHEN creation_datetime_raw != ''
                THEN creation_datetime_raw::TIMESTAMP ELSE NULL END AS scheduled_datetime
    FROM (SELECT *, RANK() OVER (PARTITION BY appointment_id
              ORDER BY CASE WHEN REGEXP_COUNT(TRIM(record_version_raw), '^-?[0-9]+\.?[0-9]*$') = 1
                            THEN TRIM(record_version_raw)::FLOAT ELSE NULL END DESC NULLS LAST) AS rnk
          FROM appointments_raw) t
    WHERE rnk = 1
),

-- equipment fallback: when primary appointment JOIN misses (~15% of trailers)
appt_by_equipment AS (
    SELECT trailer_id, facility_code, status, unit_count, carrier_code,
           ROW_NUMBER() OVER (PARTITION BY trailer_id ORDER BY scheduled_datetime DESC NULLS LAST) AS rn
    FROM appointments
    WHERE trailer_id IS NOT NULL AND status IN ('ARRIVED','CHECKED_IN','SCHEDULED','NEW')
),

-- visit lifecycle: reconstruct dwell from event stream
visit_lifecycle AS (
    SELECT equipment_visit_id, equipment_number,
           MIN(CASE WHEN event_type = 'CHECK_IN' THEN CONVERT_TIMEZONE('UTC','US/Pacific', event_time) END) AS checkin_time,
           MAX(CASE WHEN event_type IN ('CHECK_OUT','REMOVE_EQUIPMENT') THEN CONVERT_TIMEZONE('UTC','US/Pacific', event_time) END) AS checkout_time,
           COUNT(CASE WHEN event_type = 'LOCATION_AUDIT' THEN 1 END) AS location_changes
    FROM operations.yard_gate_events
    WHERE event_time > SYSDATE - INTERVAL '8 day' AND region_id = 1
    GROUP BY 1, 2
),

-- yard snapshot: deduplicate to latest per equipment
yard_positions AS (
    SELECT appointment_id, yard_building_codes, equipment_id AS trailer_id,
           is_empty, visit_reason, TRUNC(updated_timestamp::TIMESTAMP) AS snapshot_date,
           CASE WHEN owner = '' THEN operator ELSE owner END AS owner,
           location_code, equipment_visit_id
    FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY owner||equipment_id ORDER BY updated_timestamp DESC) AS rn
          FROM operations.yard_snapshot_raw
          WHERE TRUNC(updated_timestamp::TIMESTAMP) = (SELECT TRUNC(MAX(updated_timestamp)) FROM operations.yard_snapshot_raw)
            AND (asset_type ILIKE '%TRAILER%' OR asset_type IS NULL)) t
    WHERE rn = 1
),

-- final join
assembled AS (
    SELECT yp.snapshot_date, fd.facility_code, fd.facility_type, fd.region,
           yp.equipment_visit_id, yp.trailer_id AS equipment_number, yp.owner, yp.is_empty,
           COALESCE(appt.carrier_code, ae.carrier_code) AS carrier_code,
           COALESCE(appt.status, ae.status) AS appointment_status,
           COALESCE(appt.unit_count, ae.unit_count) AS unit_count,
           vl.checkin_time, vl.checkout_time, vl.location_changes,
           -- dwell hours: seconds since check-in
           CASE WHEN vl.checkin_time IS NOT NULL AND vl.checkout_time IS NULL
                THEN ROUND(DATEDIFF(SECOND, vl.checkin_time, SYSDATE) / 3600.0, 2)
                WHEN vl.checkin_time IS NOT NULL AND vl.checkout_time IS NOT NULL
                THEN ROUND(DATEDIFF(SECOND, vl.checkin_time, vl.checkout_time) / 3600.0, 2)
           END AS yard_dwell_hours,
           -- inbound classification: without this, trailer counts inflate 3x
           CASE WHEN appt.status IN ('ARRIVED','CHECKED_IN','CLOSED','DEFECT','SCHEDULED','NEW')
                     AND (LOWER(yp.visit_reason) != 'outbound' OR yp.visit_reason IS NULL)
                     AND (LOWER(yp.is_empty) != 'true' OR yp.is_empty IS NULL)
                THEN 1 ELSE 0 END AS inbound_check
    FROM yard_positions yp
    JOIN facility_dim fd ON fd.facility_code IN (
        SPLIT_PART(yp.yard_building_codes,'/',1), SPLIT_PART(yp.yard_building_codes,'/',2))
    LEFT JOIN visit_lifecycle vl ON yp.equipment_visit_id = vl.equipment_visit_id
    LEFT JOIN appointments appt ON yp.appointment_id = appt.appointment_id
    LEFT JOIN (SELECT * FROM appt_by_equipment WHERE rn = 1) ae
        ON yp.trailer_id = ae.trailer_id AND yp.appointment_id IS NULL
)
SELECT * FROM assembled;

-- production swap
TRUNCATE TABLE analytics.yard_master_live;
INSERT INTO analytics.yard_master_live SELECT * FROM analytics.yard_master_live_stg;
DROP TABLE IF EXISTS analytics.yard_master_live_stg;
