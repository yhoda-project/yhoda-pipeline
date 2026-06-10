# Entity Relationship Diagram

This diagram shows the seven tables in the YHODA database and how they relate to each other.

The `geo_lookup` table is the geography dimension - it links the other tables via geography codes. The `dataset_metadata` table links to `indicator` via the `dataset_code` field, allowing any indicator row to be traced back to the pipeline run that loaded it.

---

```mermaid
erDiagram
  geo_lookup {
    int id PK
    varchar lsoa_code UK
    varchar lsoa_name
    varchar msoa_code
    varchar msoa_name
    varchar lad_code
    varchar lad_name
    varchar region_code
    varchar region_name
  }

  indicator {
    int id PK
    varchar indicator_id
    varchar indicator_name
    varchar geography_code
    varchar geography_name
    varchar geography_level
    varchar lad_code
    varchar lad_name
    date reference_period
    float value
    varchar unit
    varchar source
    varchar dataset_code
    varchar breakdown_category
    boolean is_forecast
    varchar forecast_model
    timestamp created_at
    timestamp updated_at
  }

  dataset_metadata {
    int id PK
    varchar dataset_code
    varchar source
    varchar extraction_status
    varchar prefect_flow_run_id
    int rows_extracted
    int rows_loaded
    text error_message
    text source_url
    timestamp extracted_at
    timestamp loaded_at
    timestamp created_at
  }

  jobs_lsoa {
    int id PK
    varchar lsoa_code
    varchar lsoa_name
    varchar msoa_code
    varchar msoa_name
    varchar msoa_hcl_name
    varchar lad_code
    varchar lad_name
    int year
    int sic_code
    varchar sic_description
    varchar section
    varchar division
    varchar group_name
    int employees
    timestamp created_at
    timestamp updated_at
  }

  industry_business {
    int id PK
    int year
    varchar msoa_code
    varchar msoa_name
    varchar lad_code
    varchar lad_name
    varchar industry
    varchar turnover_band
    int business_count
    timestamp created_at
    timestamp updated_at
  }

  industry_business_kpi {
    int id PK
    varchar grouping_level
    int year
    varchar lad_code
    varchar lad_name
    varchar msoa_code
    varchar msoa_name
    varchar industry
    varchar turnover_band
    int business_count
    int business_lag3
    float pct_change_3y
    int business_lag8
    float pct_change_8y
    timestamp created_at
    timestamp updated_at
  }

  correlations {
    int id PK
    varchar indicator_1_id
    varchar indicator_2_id
    varchar indicator_1_name
    varchar indicator_2_name
    float spearman_rho
    float p_value
    boolean is_significant
    text message
    timestamp computed_at
  }

  geo_lookup ||..o{ indicator : "geography_code / lad_code"
  geo_lookup ||..o{ jobs_lsoa : "lsoa_code"
  geo_lookup ||..o{ industry_business : "msoa_code"
  geo_lookup ||..o{ industry_business_kpi : "lad_code"
  dataset_metadata ||..o{ indicator : "dataset_code"
  indicator ||..o{ correlations : "indicator_id / indicator_1_id"
  indicator ||..o{ correlations : "indicator_id / indicator_2_id"
```
