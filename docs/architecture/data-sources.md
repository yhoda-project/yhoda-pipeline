# Data Sources

The pipeline draws from eight data sources. Three are APIs that the pipeline connects to automatically each month. The remaining five are static publications that are loaded manually when a new edition is released.

---

## NOMIS

NOMIS is the ONS labour market statistics service. It provides access to large national surveys, filtered down to Yorkshire LAD level.

| Dataset | What we pull | Update frequency |
|---------|-------------|-----------------|
| Annual Population Survey (APS) | Employment rate, unemployment rate, self-employment rate, economic inactivity rate, RQF4+ qualifications, no qualifications | Annual (December reference period) |
| Annual Survey of Hours and Earnings (ASHE) | Median gross weekly earnings by workplace | Annual |
| Jobs Density | Total filled jobs as a ratio of working-age population | Annual |

The pipeline connects to NOMIS via a public API. An API key is optional for public endpoints but removes rate limits.

---

## DWP Stat-Xplore

DWP Stat-Xplore is the Department for Work and Pensions open data API for benefit claimant statistics.

| Dataset | What we pull | Update frequency |
|---------|-------------|-----------------|
| Children in Low Income Families | Count of children in households below the poverty threshold | Annual |
| Personal Independence Payment (PIP) | Count of PIP claimants | Monthly |

An API key is required. Request one from the [Stat-Xplore portal](https://stat-xplore.dwp.gov.uk/).

---

## NHS Fingertips

NHS Fingertips (fingertips.phe.org.uk) is the UKHSA Public Health Profiles API. It publishes hundreds of health indicators at LAD and sub-LAD geographies.

| Dataset | What we pull | Update frequency |
|---------|-------------|-----------------|
| Life expectancy at birth | Estimated life expectancy, male and female separately | Annual |
| Healthy life expectancy at birth | Years expected to live in good health, male and female separately | Annual |
| Under-75 preventable mortality | Preventable deaths per 100,000 population under 75 | Annual |

No API key is needed - Fingertips is a public API.

---

## ONS

ONS publishes static data releases (spreadsheets and bulk downloads) rather than a queryable API. Data from these sources is loaded manually from CSV files when a new edition is published.

| Dataset | What we pull | Update frequency |
|---------|-------------|-----------------|
| Business Demography | Business births, deaths, and survival rates by LAD | Annual |
| Regional Accounts (GVA) | Gross Value Added by LAD | Annual |
| Housing Tenure | Owner-occupied, rented, and social housing proportions | Census (every ~10 years) |
| Index of Multiple Deprivation (IMD) | Deprivation scores and deciles by LSOA | Every 4–5 years |
| Inter-Departmental Business Register (IDBR) | Employee counts by SIC code at LSOA level (preprocessed by YHODA) | Annual |

---

## Sport England

Sport England publishes the Active Lives survey - a biannual study of physical activity participation rates across England at LAD level.

| Dataset | What we pull | Update frequency |
|---------|-------------|-----------------|
| Active Lives | Proportion of adults meeting activity guidelines | Biannual |

Data is loaded manually from the preprocessed CSV when a new edition is released. There is no automated API connection.

---

## Ofcom

Ofcom's Connected Nations report provides annual broadband availability and speed statistics at LAD level.

| Dataset | What we pull | Update frequency |
|---------|-------------|-----------------|
| Connected Nations | Full-fibre and superfast broadband coverage; average download speeds | Annual |

Data is loaded manually from the published CSV.

---

## DEFRA

DEFRA's Automatic Urban and Rural Network (AURN) monitors air quality at fixed stations across England.

| Dataset | What we pull | Update frequency |
|---------|-------------|-----------------|
| AURN | Annual mean concentrations of PM2.5, PM10, NO2, and O3 | Annual |

Data is loaded manually. DEFRA also publishes a public API, which could be used to automate this in future.

---

## BEIS / DESNZ

The Department for Energy Security and Net Zero (formerly BEIS) publishes sub-national energy consumption statistics annually.

| Dataset | What we pull | Update frequency |
|---------|-------------|-----------------|
| Sub-national energy consumption | Total electricity and gas consumption by LAD | Annual |

Data is loaded manually from the GOV.UK open data release.
