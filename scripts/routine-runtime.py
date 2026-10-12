#!/usr/bin/env python3
"""Ansible-owned, affected-service deployment with immutable runtime recovery."""
import argparse
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import re
import runpy
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / 'routine-updates.json').read_text())
STATE = Path(POLICY['state_directory'])
TRANSACTION = STATE / 'routine-update.json'
ENV = '/home/github-runner-homelab/.secrets/homelab.env'


def command(*args):
    return subprocess.check_output(list(args), cwd=ROOT, text=True, stderr=subprocess.PIPE).strip()


def json_command(*args):
    return json.loads(command(*args))


def backup_gate(path=None, now=None):
    manifest = json.loads(Path(path or POLICY['backup_manifest']).read_text())
    timestamp = datetime.datetime.fromisoformat(manifest['completed_at'])
    age = ((now or datetime.datetime.now(datetime.timezone.utc)) - timestamp).total_seconds()
    if not 0 <= age <= POLICY['backup_max_age_seconds']:
        raise ValueError('active_database_backup_stale')
    if manifest['container'] != 'homelab-postgres' or not {
            'openproject', 'vaultwarden', 'mealie', 'vikunja'} <= set(manifest['databases']):
        raise ValueError('active_database_backup_coverage_missing')
    artifact = Path(manifest['artifact'])
    with artifact.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != manifest['sha256']:
        raise ValueError('active_database_backup_integrity_failed')
    with gzip.open(artifact, 'rb') as stream:
        while stream.read(1024 * 1024):
            pass


def semver(label):
    label = re.sub(r'^Linuxserver.io version:-\s*', '', label or '')
    match = re.match(r'v?(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?', label)
    return tuple(int(value) for value in match.groups() if value is not None) if match else None


def compatibility(before, after, automatic):
    old, new = semver(before), semver(after)
    if automatic and (old is None or new is None or old[0] != new[0] or new < old):
        raise ValueError('major_or_unknown_runtime_version_requires_manual_approval')
    # Never automatically undo a possible schema migration, even within a minor.
    return old is not None and new is not None and before.lstrip('v') == after.lstrip('v')


def version(image):
    labels = image.get('Config', {}).get('Labels') or {}
    return labels.get('org.opencontainers.image.version') or labels.get('build_version')


def binary_version(name, target=None):
    # Custom builds can omit OCI version labels. Read the supported application
    # interface instead of treating their image names as a version attestation.
    if name not in ('caddy', 'code-server'):
        return None
    flag = 'version' if name == 'caddy' else '--version'
    if target is None:
        return command('docker', 'exec', name, name, flag).split()[0]
    return command('docker', 'run', '--rm', '--network', 'none', '--entrypoint', name,
                   target, flag).split()[0]


def compose(source, *args):
    return command('docker', 'compose', '--project-directory',
                   '/srv/homelab/' + str(Path(source).parent), '--env-file', ENV,
                   '-f', str(ROOT / source), *args)


def media_gate(services):
    if not set(services) & set(POLICY['media_order']):
        return
    source = command('findmnt', '-n', '-o', 'SOURCE', '--target', '/mnt/wood-server-nas/media')
    if source != '192.168.1.10:/volume1/media':
        raise ValueError('media_mount_source_mismatch')
    for name in ('Movies', 'TV Shows'):
        if not Path('/mnt/wood-server-nas/media/library', name).is_dir():
            raise ValueError('media_readiness_path_missing')


def write(plan):
    # Root-owned transaction contains source paths and image identities, no env values.
    if not STATE.is_dir():
        raise ValueError('deployment_state_directory_missing')
    temp = TRANSACTION.with_suffix('.tmp')
    temp.write_text(json.dumps(plan, sort_keys=True) + '\n')
    temp.chmod(0o600)
    temp.replace(TRANSACTION)


def plan(automatic):
    state = json.loads((STATE / 'homelab.json').read_text())
    base = state['current_release']
    head = command('git', 'rev-parse', 'HEAD')
    command('git', 'merge-base', '--is-ancestor', base, head)
    files = command('git', 'ls-files', 'compose').splitlines()
    changed = set(command('git', 'diff', '--name-only', base, head).splitlines())
    if automatic:
        # Publication approval never authorizes pending manual runtime changes.
        classify = runpy.run_path(str(ROOT / 'scripts/routine-policy.py'))['image_changes']
        for source in sorted(changed):
            try:
                classify(source, command('git', 'show', base + ':' + source),
                         command('git', 'show', head + ':' + source), POLICY['protected_packages'])
            except ValueError as error:
                raise ValueError('undeployed_manual_changes_require_manual_approval') from error
    result = {'revision': head, 'base': base, 'automatic': automatic,
              'services': [], 'sources': [], 'disabled': [], 'rollback_safe': True}
    for source in files:
        if not source.endswith(('.yml', '.yaml')) or source.endswith('compose.infisical.yml'):
            continue
        config = json.loads(compose(source, 'config', '--format', 'json'))
        for service, definition in config['services'].items():
            if service.endswith(('init', 'seeder')):
                continue
            name = definition.get('container_name', service)
            build = definition.get('build')
            build_changed = bool(build and any(f.startswith(str(Path(source).parent) + '/') and
                                              not f.endswith(('.yml', '.yaml')) for f in changed))
            if source not in changed and not build_changed:
                continue
            inspect = json_command('docker', 'inspect', name)[0]
            if name in POLICY['disabled_containers']:
                if inspect['State']['Status'] == 'running':
                    raise ValueError('disabled_service_is_running_review_required')
                result['disabled'].append(name)
                continue
            old = json_command('docker', 'image', 'inspect', inspect['Image'])[0]
            target = definition['image']
            mods = definition.get('environment', {}).get('DOCKER_MODS')
            current_env = dict(v.split('=', 1) for v in inspect['Config'].get('Env', []) if '=' in v)
            mod_changed = mods and mods != current_env.get('DOCKER_MODS')
            if mod_changed and '@sha256:' not in mods:
                raise ValueError('effective_mod_image_is_not_pinned')
            if not build and '@sha256:' not in target:
                raise ValueError('effective_image_is_not_pinned')
            if not build and not mod_changed and target.split('@')[-1] in ' '.join(old.get('RepoDigests', [])):
                continue
            if build and not build_changed:
                continue
            if name == 'caddy':
                declared = re.search(r'^ARG CADDY_VERSION=(\S+)',
                                     (ROOT / Path(source).parent / 'Dockerfile').read_text(), re.M)[1]
                if config['services'][service]['build'].get('args', {}).get('CADDY_VERSION') != declared:
                    raise ValueError('caddy_build_version_override_is_not_approved')
            if inspect['State']['Status'] != 'running':
                raise ValueError('affected_service_is_not_running')
            package = target.split('@')[0].split(':')[0]
            if automatic and package in POLICY['protected_packages']:
                raise ValueError('protected_service_requires_manual_approval')
            row = {'source': source, 'service': service, 'container': name, 'target': target,
                   'build': bool(build), 'before_id': inspect['Image'],
                   'before_version': version(old) or binary_version(name),
                   'restart': inspect['HostConfig']['RestartPolicy']['Name'], 'mods': mods}
            result['services'].append(row)
            result['sources'].append(source)
            if build_changed:
                result['sources'].extend(f for f in changed if f in files and
                                        f.startswith(str(Path(source).parent) + '/'))
    result['sources'] = sorted(set(result['sources']))
    result['services'].sort(key=lambda r: (POLICY['media_order'].index(r['container'])
                                          if r['container'] in POLICY['media_order'] else 100,
                                          r['container']))
    media_gate([r['container'] for r in result['services']])
    if result['services']:
        backup_gate()
    return result


def endpoint(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            code = response.status
    except urllib.error.HTTPError as error:
        code = error.code
    if code not in (200, 201, 204, 301, 302, 303, 307, 308, 401, 403):
        raise ValueError('affected_endpoint_failed')


def verify(row, recovering=False):
    expected = row['before_id'] if recovering else row['expected_id']
    for _ in range(30):
        container = json_command('docker', 'inspect', row['container'])[0]
        health = container['State'].get('Health', {}).get('Status', 'none')
        if container['Image'] != expected:
            raise ValueError('approved_image_identity_mismatch')
        if row.get('mods') and not recovering:
            if 'DOCKER_MODS=' + row['mods'] not in container['Config'].get('Env', []):
                raise ValueError('approved_mod_identity_mismatch')
        if container['State']['Status'] == 'running' and health in ('healthy', 'none'):
            if container['HostConfig']['RestartPolicy']['Name'] != row['restart']:
                raise ValueError('restart_policy_changed')
            try:
                if url := POLICY['endpoints'].get(row['container']):
                    endpoint(url)
                if internal := POLICY.get('container_endpoints', {}).get(row['container']):
                    addresses = [n['IPAddress'] for n in container['NetworkSettings']['Networks'].values()
                                 if n.get('IPAddress')]
                    if not addresses:
                        raise ValueError('affected_endpoint_address_missing')
                    endpoint(f"http://{addresses[0]}:{internal['port']}{internal['path']}")
                return
            except (ValueError, OSError):
                pass
        time.sleep(4)
    raise ValueError('affected_container_health_failed')


def apply(automatic):
    transaction = plan(automatic)
    # Persist before any pull/build/start so the existing recovery step can inspect it.
    write(transaction)
    for row in transaction['services']:
        command('docker', 'image', 'tag', row['before_id'],
                'homelab-rollback/' + row['container'] + ':' + transaction['revision'][:12])
        if row['build']:
            compose(row['source'], 'build', row['service'])
            if row['container'] == 'caddy':
                modules = command('docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'caddy',
                                  row['target'], 'list-modules')
                if 'dns.providers.cloudflare' not in modules:
                    raise ValueError('caddy_cloudflare_module_missing')
                caddy_version = command('docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'caddy',
                                         row['target'], 'version').split()[0]
                if caddy_version.lstrip('v') != (ROOT / 'compose/platform/caddy/Dockerfile').read_text().splitlines()[0].split('=')[1]:
                    raise ValueError('caddy_binary_version_mismatch')
                compose(row['source'], 'run', '--rm', '--no-deps', '--entrypoint', 'caddy',
                        row['service'], 'validate', '--config', '/etc/caddy/Caddyfile')
        else:
            command('docker', 'pull', row['target'])
        candidate = json_command('docker', 'image', 'inspect', row['target'])[0]
        row['expected_id'] = candidate['Id']
        if not row['build'] and row['target'].split('@')[-1] not in ' '.join(candidate.get('RepoDigests', [])):
            raise ValueError('pulled_digest_mismatch')
        row['after_version'] = version(candidate) or binary_version(row['container'], row['target'])
        safe = compatibility(row['before_version'], row['after_version'], automatic)
        row['rollback_safe'] = safe
        write(transaction)
        if row['target'].startswith('openproject/openproject:') and not transaction.get('openproject_migrated'):
            # The tracked seeder is the supported upgrade path. Run it once
            # before any new web/worker/cron process sees the database.
            transaction['migration_risk'] = not safe
            transaction['rollback_safe'] = transaction['rollback_safe'] and safe
            write(transaction)
            compose(row['source'], 'run', '--rm', '--no-deps', '--pull', 'never', 'projects-seeder')
            transaction['openproject_migrated'] = True
            write(transaction)
        media_gate([row['container']])
        row['applied'] = True
        transaction['rollback_safe'] = not transaction.get('migration_risk', False) and all(
            r.get('rollback_safe', True) for r in transaction['services'] if r.get('applied'))
        write(transaction)
        compose(row['source'], 'up', '-d', '--no-deps', '--no-build', '--force-recreate', '--pull', 'never', row['service'])
        verify(row)
    transaction['outcome'] = 'success'
    write(transaction)


def rollback():
    transaction = json.loads(TRANSACTION.read_text())
    if not transaction['rollback_safe']:
        raise ValueError('schema_downgrade_safety_unverified_manual_recovery_required')
    if transaction['revision'] != command('git', 'rev-parse', 'HEAD'):
        raise ValueError('recovery_evidence_revision_mismatch')
    for row in transaction['services']:
        if not row.get('applied'):
            continue
        media_gate([row['container']])
        # Exact old tracked definition and old image ID; never a floating tag lookup.
        previous = command('git', 'show', transaction['base'] + ':' + row['source'])
        original = STATE / 'rollback-compose.yml'
        override = STATE / 'rollback-image.json'
        original.write_text(previous + '\n')
        override.write_text(json.dumps({'services': {row['service']: {'image': row['before_id']}}}))
        command('docker', 'compose', '--project-directory', '/srv/homelab/' + str(Path(row['source']).parent),
                '--env-file', ENV, '-f', str(original), '-f', str(override),
                'up', '-d', '--no-deps', '--no-build', '--pull', 'never', row['service'])
        verify(row, recovering=True)
    transaction['rolled_back'] = True
    transaction['outcome'] = 'recovered'
    for source in transaction['sources']:
        destination = STATE / 'rollback-sources' / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(command('git', 'show', transaction['base'] + ':' + source) + '\n')
    write(transaction)
    print(json.dumps({'sources': transaction['sources']}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['check', 'apply', 'health', 'rollback'])
    parser.add_argument('--manual', action='store_true')
    args = parser.parse_args()
    try:
        if args.operation == 'check':
            result = plan(not args.manual)
            print(json.dumps({'revision': result['revision'], 'sources': result['sources'],
                              'affected': [r['container'] for r in result['services']],
                              'disabled': result['disabled']}))
        elif args.operation == 'apply':
            apply(not args.manual)
        elif args.operation == 'rollback':
            rollback()
        else:
            transaction = json.loads(TRANSACTION.read_text())
            if transaction['revision'] != command('git', 'rev-parse', 'HEAD'):
                raise ValueError('health_evidence_revision_mismatch')
            for row in transaction['services']:
                verify(row, transaction.get('rolled_back', False))
        return 0
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        # Never print Docker config, environment values or captured subprocess output.
        reason = str(error) if isinstance(error, ValueError) and re.fullmatch(r'[a-z_]+', str(error)) else 'prerequisite_or_command_failed'
        print(json.dumps({'status': 'blocked_or_failed', 'operation': args.operation, 'reason': reason}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
