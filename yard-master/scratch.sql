-- scratch queries i run when something looks off in the WBR numbers

-- quick check: how many trailers are we classifying as inbound today vs yesterday?
-- if this jumps by >5000 something is wrong with the classification logic
select snapshot_date, count(*) as total, sum(inbound_check) as inbound
from analytics.yard_master_live
group by 1 order by 1 desc limit 5;

-- are any FCs showing 0 inbound that had >100 yesterday? usually means a source table didnt refresh
select facility_code, sum(inbound_check) as today_inbound
from analytics.yard_master_live
where snapshot_date = current_date
group by 1
having sum(inbound_check) = 0
  and facility_code in (
    select facility_code from analytics.yard_master_hist
    where snapshot_date = current_date - 1
    group by 1 having sum(inbound_check) > 100
  );

-- dwell sanity: avg should be ~2.5 days network-wide. if its >4 or <1.5, investigate
select round(avg(yard_dwell_hours / 24.0), 2) as avg_dwell_days,
       count(*) as trailer_count
from analytics.yard_master_live
where inbound_check = 1 and yard_dwell_hours > 0;
