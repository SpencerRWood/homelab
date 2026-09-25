# Infisical runtime secrets

The `Homelab` project has one `homelab` environment and the service paths
`/mealie`, `/vikunja`, `/openproject`, `/caddy`, and `/vaultwarden`.
`homelab-deployer` has Universal Auth,
organization `no-access`, and the built-in project `Viewer` role. Viewer is
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
and `rollback-infisical-service vikunja|openproject|caddy|vaultwarden` restore
only the selected service's Compose file and legacy `homelab.env`; rollback
does not delete Infisical secrets.

The legacy env file remains until a separate cleanup tranche. PostgreSQL,
dev infrastructure, GitHub Actions, media-managed
settings, runner credentials, and stale or recovered instances are outside this
migration.
