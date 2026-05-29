#!/usr/bin/env bash
# One-time setup script for staging and prod VMs.
# To be run as a user with sudo privileges from /opt/yhoda
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Symlinking systemd service files..."
sudo ln -sf "$DEPLOY_DIR/prefect-server.service" /etc/systemd/system/prefect-server.service
sudo ln -sf "$DEPLOY_DIR/prefect-worker.service" /etc/systemd/system/prefect-worker.service

echo "Reloading systemd..."
sudo systemctl daemon-reload

echo "Enabling services..."
sudo systemctl enable prefect-server prefect-worker

echo "Starting services..."
sudo systemctl start prefect-server
sleep 15
sudo systemctl start prefect-worker

echo "Done. Check status with:"
echo "  sudo systemctl status prefect-server prefect-worker"
