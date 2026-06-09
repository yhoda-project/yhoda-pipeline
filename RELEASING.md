# Releasing

Releases are fully automated via [release-please](https://github.com/googleapis/release-please).
**You do not need to manually bump version numbers or write changelogs.**

---

## How it works

1. Merge pull requests to `main` using [Conventional Commits](#conventional-commits).
2. release-please opens (or updates) a **Release PR** that:
   - bumps the version in `pyproject.toml`
   - updates `CHANGELOG.md` based on commit messages since the last release
3. When the Release PR is merged to `main`:
   - a Git tag is created (e.g. `v1.2.3`)
   - a GitHub Release is published with the generated changelog

No manual steps are required.

---

## Conventional Commits

Commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) spec.
release-please uses these to determine the next version and to generate the changelog.

| Prefix | Meaning | Version bump |
|--------|---------|--------------|
| `feat:` | New feature | **minor** (0.x.0) |
| `fix:` | Bug fix | patch (0.0.x) |
| `perf:` | Performance improvement | patch |
| `refactor:` | Code refactor with no behaviour change | patch |
| `chore:` / `docs:` / `ci:` | Non-functional | patch (hidden in changelog) |
| `feat!:` / `fix!:` / any `BREAKING CHANGE:` footer | Breaking change | **major** (x.0.0) |

### Examples

```
feat: add ONS mid-year population extract task

fix: handle null values in DWP claimant response

feat!: rename indicator_id column to obs_id

BREAKING CHANGE: the Indicator primary key column has been renamed.
```

---

## Triggering a release manually

You should never need to do this, but if the Release PR was accidentally closed:

```bash
# Re-open it by pushing a new conventional commit to main, or
# use the GitHub UI to re-run the "Release Please" workflow.
```

---

## Pre-releases and release candidates

release-please does not currently generate pre-release tags for this project.
For testing a release candidate, deploy from a feature branch manually using:

```bash
uv run prefect deploy --all --no-prompt
```

---

## Secrets required

The workflow uses the built-in `GITHUB_TOKEN` - no additional secrets are needed for the
release automation itself.
