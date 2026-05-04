
    
    

select
    ticker_sk as unique_field,
    count(*) as n_records

from "pipeline"."main"."dim_ticker"
where ticker_sk is not null
group by ticker_sk
having count(*) > 1


