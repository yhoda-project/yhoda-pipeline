# YHODA Pipeline Documentation

This site documents the YHODA data pipeline - the automated system that collects, validates, and stores socioeconomic, health, and environmental data for Yorkshire, powering the [Yorkshire Vitality Suite](https://yorkshireportal.org/vitality-suite) dashboards.

---

## What this system does

Every month, the pipeline automatically:

1. Pulls fresh data from source APIs (NOMIS, NHS Fingertips, DWP Stat-Xplore)
2. Validates and transforms it into a consistent format
3. Stores the results in a central PostgreSQL database
4. Logs each run's status, row counts, and any errors

The database feeds directly into the [Yorkshire Vitality Suite Power BI dashboards](https://yorkshireportal.org/vitality-suite).

---

## Who this documentation is for

These docs are written for the YHODA research team and technical staff who maintain and use the pipeline.
You do not need to be a software developer, but familiarity with the project and its data will help.

---

## Got a question?

[Ask DeepWiki](https://deepwiki.com/yhoda-project/yhoda-pipeline) - an AI assistant trained on this repository that can answer questions about how the pipeline works, where to find things, and how components fit together.

---

## How these docs are structured

| Section | What's in it |
|---------|-------------|
| [Onboarding](onboarding.md) | How to get set up as a new team member |
| [Architecture](architecture/overview.md) | How the system works |
| [How-to guides](how-to/query-the-database.md) | Step-by-step instructions for common tasks |
| [Runbooks](runbooks/index.md) | What to do when something goes wrong |
| [Reference](reference/environment-variables.md) | Technical reference material |
