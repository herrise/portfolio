
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select timestamp_utc
from "pipeline"."main"."dim_time"
where timestamp_utc is null



  
  
      
    ) dbt_internal_test