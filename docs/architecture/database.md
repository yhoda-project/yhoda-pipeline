# Database

The pipeline stores all its data in a PostgreSQL database called `yhoda_dev` (staging) or `yhoda_prod` (production). There are six tables.

See [Query the database](../how-to/query-the-database.md) for instructions on connecting and running queries.

---

## Tables

### `indicator`

The main data table. Every socioeconomic, health, or environmental figure the pipeline collects ends up here as a single row.

Each row represents one measurement - for example, "the employment rate in Sheffield for April 2024 was 73.5%." The table holds data at three geography levels:

| Level | What it means |
|-------|--------------|
| LAD | Local Authority District - e.g. Sheffield, Bradford, Leeds |
| MSOA | Middle Super Output Area - a sub-district neighbourhood |
| LSOA | Lower Super Output Area - a smaller neighbourhood |

The combination of indicator, geography, time period, and breakdown category is unique - re-running a flow updates the existing row rather than creating a duplicate.

---

### `dataset_metadata`

A log of every pipeline run. One row is written each time a flow loads a dataset.

This table is the first place to look if you think a dataset has not been updated or a flow has failed. It records:

- Which dataset was loaded and when
- How many rows were extracted from the source and how many were loaded into the database
- Whether the run succeeded or failed
- The error message if it failed

---

### `geo_lookup`

A geography reference table mapping the ONS hierarchy: LSOA → MSOA → LAD → Region.

This table is populated once when the pipeline is first set up and does not change unless the ONS updates its geography boundaries.

---

### `jobs_lsoa`

Employee counts broken down by industry (SIC code) at LSOA level. This powers the Jobs dashboard.

Data comes from a preprocessed CSV file and is loaded once per release.

---

### `industry_business`

Business counts by industry and turnover band at MSOA level. This powers the Industry dashboard.

---

### `industry_business_kpi`

Pre-calculated business count change statistics - 3-year and 8-year percentage changes - at Yorkshire-wide, LAD, and MSOA level. These figures are calculated when the data is loaded and stored ready for the dashboard to display without further calculation.

---

## Entity relationship diagram

See [Entity relationship diagram](../reference/entity-relationship-diagram.md) for a full diagram showing how the tables link to each other.
