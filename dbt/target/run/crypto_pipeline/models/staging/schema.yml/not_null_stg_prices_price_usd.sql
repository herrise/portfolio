
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select price_usd
from "pipeline"."main"."stg_prices"
where price_usd is null



  
  
      
    ) dbt_internal_test