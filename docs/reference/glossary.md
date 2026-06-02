# Glossary

---

## Geography

LAD - Local Authority District. The primary geography used in the pipeline. Yorkshire has 22 LADs, including Sheffield, Leeds, Bradford, and Hull. Most indicators in the database are held at LAD level.

LSOA - Lower Super Output Area. A small neighbourhood geography, typically containing around 1,500 people. Used in the Neighbourhoods and Jobs dashboards.

MSOA - Middle Super Output Area. A slightly larger neighbourhood geography, typically containing around 8,000 people. Used in the Industry dashboard.

OA - Output Area. The smallest ONS geography, below LSOA. Not currently used in the pipeline.

---

## Pipeline concepts

ETL - Extract, Transform, Load. The three stages of the pipeline: extracting data from a source, transforming it into the right format, and loading it into the database.

Prefect - The workflow orchestration tool the pipeline is built on. It handles scheduling, retries, logging, and provides the UI where you can monitor flow runs.

Flow - A self-contained Prefect script that handles one dataset or group of related datasets. The pipeline has 15 flows across three domains (economy, society, environment).

Deployment - A registered version of a flow in Prefect, with a schedule attached. Deployments appear in the Prefect UI and are what the scheduler triggers each month.

Work pool - A Prefect concept for grouping where flows run. The pipeline uses a single work pool called `yhovi-default`.

Upsert - A database operation that inserts a new row if it does not already exist, or updates the existing row if it does. The pipeline uses upserts so that re-running a flow does not create duplicate data.

Alembic - The database migration tool used to manage changes to the database schema. When a new column or table is added, an Alembic migration is created to apply the change safely.

---

## Data sources

NOMIS - The ONS Labour Market Statistics service. Provides access to national surveys including the Annual Population Survey (APS) and Annual Survey of Hours and Earnings (ASHE) at LAD level.

DWP - Department for Work and Pensions. Provides benefit claimant statistics via Stat-Xplore, including PIP claimants and children in low income families.

ONS - Office for National Statistics. The UK's national statistics authority. Publishes data on business demography, GVA, housing, and census results. Most ONS data is loaded from static CSV files rather than an API.

NHS Fingertips - The UKHSA Public Health Profiles platform. Provides health outcome indicators at LAD level, including life expectancy and preventable mortality.

---

## Project acronyms

YHODA - Yorkshire & Humber Office for Data Analytics. The organisation this pipeline was built for.

YVS - Yorkshire Vitality Suite. The collection of [Power BI dashboards](https://yorkshireportal.org/vitality-suite) that the pipeline feeds.

YEP - Yorkshire Engagement Portal. The web platform hosting the Yorkshire Vitality Suite, at yorkshireportal.org.
