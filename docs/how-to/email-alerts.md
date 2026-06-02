# Email Alerts

The pipeline sends automatic email alerts whenever a flow fails or encounters a problem. This page explains how the system works, what the emails look like, and how to set it up.

---

## How it works

Each flow in the pipeline runs on a monthly schedule. If a flow fails, it automatically sends an email to the configured recipient. No manual monitoring is required - you only hear about it when something goes wrong.

Alerts are sent via Gmail SMTP using a configured University of Sheffield email account.

---

## What the emails look like

Every alert email has a subject line with a severity tag:

```
[ERROR] YHODA Pipeline: economy-claimant-count
[WARNING] YHODA Pipeline: society-health-outcomes
[SUCCESS] YHODA Pipeline: economy-earnings
```

The body contains:

```
Flow:      economy-claimant-count
Severity:  ERROR
Time:      28 May 2026 at 06:01 UTC
Message:   DWP Stat-Xplore: invalid or missing API key (HTTP 401)

No action is needed from you right now. The pipeline will retry
automatically on its next scheduled run.

If this issue keeps happening, please contact the YHODA technical team.
```

---

## Severity levels

| Level | Triggers email | Meaning |
|-------|---------------|---------|
| ERROR | Yes | Flow failed and could not complete |
| WARNING | Yes | Flow completed but with issues |
| SUCCESS | Yes (if enabled) | Flow completed successfully |
| INFO | No | Routine log message (logs only) |

---

## What to do when you receive an alert

ERROR - the pipeline failed to update that dataset this month. The data in the database is not corrupted; it simply was not updated. The pipeline will retry automatically next month (or sooner if manually triggered). If the same flow keeps failing, contact the YHODA technical team.

WARNING - the pipeline ran but something was unusual (e.g. fewer rows than expected). Worth noting but no immediate action required.

SUCCESS - confirmation that a flow ran and updated the database successfully. These are off by default. Set `ALERT_SUCCESS_ENABLED=true` in `.env` to enable them, or remove that line to turn them off again.

---

## Setup

The alert system requires environment variables set in the `.env` file on the VM.

| Variable | Description |
|----------|-------------|
| `SMTP_USERNAME` | Sheffield university email used to send alerts |
| `SMTP_PASSWORD` | Google App Password (not your normal password) |
| `ALERT_GROUP_EMAIL` | Email address(es) that receive the alerts |
| `ALERT_SUCCESS_ENABLED` | Set to `true` to receive emails on successful runs |

`ALERT_GROUP_EMAIL` can be a single address or a comma-separated list:

```
ALERT_GROUP_EMAIL=your.email@sheffield.ac.uk
```

Success emails are off by default. To enable them:

```
ALERT_SUCCESS_ENABLED=true
```

---

## Generating a Google App Password

A Google App Password is a one-time 16-character code that allows the pipeline to send email on behalf of your account without using your normal password.

1. Go to `myaccount.google.com` and sign in with your University of Sheffield account
2. Go to Security → 2-Step Verification (must be enabled)
3. Scroll to App passwords and click it
4. Enter a name (e.g. `YHODA Pipeline`) and click Create
5. Copy the 16-character code - this is your `SMTP_PASSWORD`

Keep this code secure in your `.env` file. If it is compromised, revoke it at the same page and generate a new one. See [API key has expired](../runbooks/api-key-expired.md) for the rotation process.

---

## Built-in protections

The alert system has two built-in safeguards to prevent email overload:

Deduplication - if the same error occurs multiple times within 30 minutes (e.g. a flow retrying), only one email is sent.

Rate limiting - no more than 10 emails per minute are sent, regardless of how many flows fail simultaneously.
