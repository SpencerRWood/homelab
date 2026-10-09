# Infisical runtime secrets

The `Homelab` project has one `homelab` environment and the service paths
`/mealie`, `/vikunja`, `/openproject`, `/caddy`, `/vaultwarden`, and
`/postgres`, and `/pg-dev`. `homelab-deployer` has Universal Auth, organization `no-access`,
and the built-in project `Viewer` role. Viewer is
project-wide. The trusted root-owned deployment layer is the security boundary:
application containers receive generated environment files and never receive
Infisical credentials.

The credential lives only at
`/srv/homelab/secrets/bootstrap/infisical-homelab.json` on the Beelink. It has
root:root ownership and mode `0600`, inside a root:root `0700` directory. The
file contains only the API URL, project ID, client ID, and client secret.

One `resolve-infisical-env` command accepts an environment, path, output file,
and required keys. It validates all required values, writes only those keys to
an atomic root:root `0600` runtime file, and preserves the prior file on error.
Errors are sanitized. The required keys and Compose services are declared in
`infisical_runtime_services` in Ansible group variables. The generic
`deploy-infisical-service` command resolves first, validates Compose, and then
reconciles only the declared application services. The
`homelab-infisical@.service` template runs this command at boot; the canonical
Ansible playbook refreshes all declared runtime files before Compose checks.

To deploy an individual migrated service from this checkout, run the
`ansible/playbooks/homelab-infisical.yml` playbook with
`infisical_selected_services` set to that service. The playbook retains the
previous Compose definition before a first switch. `rollback-mealie-infisical`
and `rollback-infisical-service vikunja|openproject|caddy|vaultwarden|postgres|pg-dev`
restore only the selected service's Compose file and retained legacy source;
rollback does not delete Infisical secrets.

The legacy env file remains until a separate cleanup tranche. The dedicated
`homelab-postgres` container consumes `POSTGRES_PASSWORD` from the protected
`/srv/homelab/secrets/runtime/postgres.env`; its initialized database role
password was not changed. `pg-dev` uses a separate protected
`/srv/homelab/secrets/runtime/pg-dev.env` and the retained PostgreSQL 18
`dev_pgdata` volume. Its previous credential was recovered from the active
container after an authenticated query and is retained at
`/srv/homelab/secrets/rollback/pg-dev.env` for service-specific rollback.
The previous Compose definition is retained in the pg-dev directory. A rollback
does not remove or reinitialize the volume. Legacy-postgres is decommissioned
and is not an Infisical target. GitHub Actions, media-managed settings, runner
credentials, and stale or recovered instances remain outside this runtime
migration.
