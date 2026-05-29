# Security Policy

## Supported Versions

YHODA is under active development. Only the latest commit on the `main` branch
receives security fixes. No versioned releases have been published yet.

| Branch / Version | Supported          |
| ---------------- | ------------------ |
| `main` (latest)  | :white_check_mark: |
| Any older commit | :x:                |

## Reporting a Vulnerability

Please do not report security vulnerabilities through public GitHub issues.

Report vulnerabilities privately by emailing:

yhoda@sheffield.ac.uk

Include as much of the following as possible:

- A description of the vulnerability and its potential impact
- The component or file affected (e.g. a specific module, API endpoint, or
  configuration file)
- Steps to reproduce or a proof-of-concept (if safe to share)
- Any suggested mitigations you have identified

## Security Design

### CI/CD

- GitHub Actions workflows run in isolated environments; secrets are injected
  via GitHub encrypted secrets and are never echoed to logs
- The deploy step runs only on push to `main` after lint, type-check, and test
  stages all pass

### Dependency management

- Dependencies are pinned via `uv.lock` and reviewed on each update
- `uv sync` is used for reproducible installs; `pip install` is not used in
  CI or production
- Pre-commit hooks enforce linting (`ruff`) and type-checking (`mypy`) before
  any commit reaches the remote

### Data handling

- The pipeline processes publicly available statistical data; no personal data
  (PII) is ingested or stored
- Disclosure-controlled suppressed values are stored as `NULL`, not imputed
- Access to the databases is restricted to the YHODA
  team via SSH tunnelling through the university VPN
