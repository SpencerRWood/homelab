#!/usr/bin/env bash
# Check only containers which the current host actually has deployed.  Several
# Compose definitions are intentionally staged, so an absent container is not a
# deployment failure.
set -euo pipefail

/usr/bin/ansible --connection=local -i ansible/inventory/homelab.yml homelab -b \
  -m script -a scripts/health-check-remote.sh
