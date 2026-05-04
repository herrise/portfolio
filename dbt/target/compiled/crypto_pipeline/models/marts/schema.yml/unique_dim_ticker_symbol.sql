
    
    

select
    symbol as unique_field,
    count(*) as n_records

from "pipeline"."main"."dim_ticker"
where symbol is not null
group by symbol
having count(*) > 1


