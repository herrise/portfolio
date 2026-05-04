
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    symbol as unique_field,
    count(*) as n_records

from "pipeline"."main"."dim_ticker"
where symbol is not null
group by symbol
having count(*) > 1



  
  
      
    ) dbt_internal_test