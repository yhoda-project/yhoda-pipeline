# Deployment Setup

## First-time setup

1. In `prefect-server.service` and `prefect-worker.service`, replace
   `REPLACE_WITH_SERVICE_USER` with the actual service account username on the VM (e.g sa_test_user).
2. Run `bash deploy/setup.sh` from `/opt/yhoda` to install and start the Prefect server and worker as persistent background services.
