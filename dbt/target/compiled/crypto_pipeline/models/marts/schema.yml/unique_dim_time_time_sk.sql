
    
    

select
    time_sk as unique_field,
    count(*) as n_records

from "pipeline"."main"."dim_time"
where time_sk is not null
group by time_sk
having count(*) > 1


