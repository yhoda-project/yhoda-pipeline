# YHODA Project Plan - Phase 2 Implementation

> **Timeline:** Feb 2026 – Jun 2026
> **Goal:** Automate ETL pipelines for ~40 priority datasets across 22 Yorkshire LADs

---

## Milestone 1: Shared Infrastructure (Feb 24 – Mar 14)

Core plumbing that every flow depends on.

| # | Item | Target | Priority |
|---|------|--------|----------|
| 1 | Secure API Credentials (Nomis, ONS, DWP) | Mar 7 | Critical |
| 2 | Database Setup and Geography Layer | Mar 7 | Critical |
| 3 | Shared Transform and Load Pipeline | Mar 14 | Critical |

---

## Milestone 2: Prototype Ingestion (Mar 10 – Apr 24)

Working API connectors for Nomis, ONS, and DWP - the **End-Apr deliverable**.

| # | Item | Target | Priority |
|---|------|--------|----------|
| 4 | Nomis and ONS API Connectors | Mar 28 | High |
| 5 | DWP Stat-Xplore Connector | Mar 21 | High |
| 6 | Prototype Economy Flows (3 flows) | Apr 11 | High |
| 7 | Prototype Testing and Milestone Review | Apr 24 | High |

---

## Milestone 3: Scale-out (Apr 28 – May 29)

Extend to remaining priority datasets; improve validation and error handling.

| # | Item | Target | Priority |
|---|------|--------|----------|
| 8 | Remaining Extract Connectors (5 sources) | May 15 | Medium |
| 9 | Remaining Flows and Orchestrator (10 flows) | May 26 | Medium |
| 10 | Quality Hardening and Full Test Suite | May 29 | Medium |

---

## Milestone 4: Handover (Jun 1 – Jun 26)

Documentation, training, and project close.

| # | Item | Target | Priority |
|---|------|--------|----------|
| 11 | Documentation and Runbooks | Jun 12 | High |
| 12 | CI/CD Hardening and Monitoring | Jun 19 | Medium |
| 13 | Team Training and Project Handover | Jun 26 | Critical |

---

## Critical Path

```
Secure API Credentials (Feb 24)
    ↓
Database Setup + Shared Pipeline (Feb 24 – Mar 14)
    ↓
Nomis / ONS / DWP Connectors (Mar 10 – Mar 28)
    ↓
Prototype Economy Flows (Mar 24 – Apr 11)
    ↓
★ PROTOTYPE DEMO (Apr 24)
    ↓
Remaining Connectors + Flows (Apr 28 – May 26)
    ↓
★ SCALE-OUT REVIEW (May 29)
    ↓
Docs + Training (Jun 1 – Jun 22)
    ↓
★ HANDOVER SIGN-OFF (Jun 26)
```

## Key Risks

| Risk | Mitigation |
|------|-----------|
| API credential delays | Start registration immediately; develop against mocked responses in parallel |
| Geography fragmentation | Prioritise GeoLookup population early; validate LSOA→LAD mappings before building connectors |
| Sport England / BEIS APIs TBC | May need CSV download fallback; scope during scale-out |
| Timeline pressure (~40 datasets) | Focus on Nomis/ONS/DWP prototype first; narrow remaining scope if needed |
