
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select ticker_sk
from "pipeline"."main"."fct_price_snapshots"
where ticker_sk is null



  
  
      
    ) dbt_internal_test