"""Exercise authorization, affected rollout and recovery without runtime access."""
import datetime
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


POLICY = load('routine-policy')
MAIN_POLICY = load('main-deployment-policy')
RUNTIME = load('routine-runtime')
DIGEST = 'sha256:' + 'a' * 64
NEXT = 'sha256:' + 'b' * 64


class RoutinePolicyTests(unittest.TestCase):
    def test_main_delivery_accepts_human_and_bot_commits_but_rejects_other_events(self):
        env = {'GITHUB_EVENT_NAME': 'push', 'GITHUB_REF': 'refs/heads/main',
               'GITHUB_SHA': 'approved', 'EXPECTED_REVISION': 'approved'}
        with patch.object(MAIN_POLICY.subprocess, 'check_output', return_value='approved\n'):
            for actor in ('SpencerRWood', 'renovate[bot]'):
                with patch.dict(os.environ, env | {'GITHUB_ACTOR': actor}, clear=True):
                    self.assertTrue(MAIN_POLICY.authorize()['authorized'])
            for changes in ({'GITHUB_EVENT_NAME': 'pull_request'}, {'GITHUB_REF': 'refs/heads/feature'},
                            {'GITHUB_SHA': 'different'}, {'EXPECTED_REVISION': 'different'}):
                with patch.dict(os.environ, env | changes, clear=True), self.assertRaises(ValueError):
                    MAIN_POLICY.authorize()

    def test_main_delivery_preserves_the_backup_only_integration_exception(self):
        document = yaml.safe_load((ROOT / '.github/workflows/release.yml').read_text())
        self.assertNotIn('policy', document['jobs'])
        release = document['jobs']['release']
        self.assertEqual(release['needs'], 'delivery-scope')
        self.assertIn("needs.delivery-scope.outputs.automatic_delivery == 'true'", release['if'])
        self.assertNotIn('eligible', release['if'])
        self.assertIn('scripts/main-deployment-policy.py', release['with']['automatic_policy_command'])
        deploy = document['jobs']['deploy']
        self.assertEqual(deploy['needs'], 'release')
        self.assertIn("github.ref == 'refs/heads/main'", deploy['if'])
        self.assertIn("github.event_name == 'push'", deploy['if'])
        self.assertEqual(deploy['with']['ref'], '${{ needs.release.outputs.release_tag || github.sha }}')
        self.assertTrue(deploy['with']['automatic'])
    def test_digest_patch_minor_and_custom_references(self):
        for old, new in [('latest', 'latest'), ('1.2.3', '1.2.4'), ('1.2', '1.3')]:
            before = f'services:\n  app:\n    image: example/app:{old}@{DIGEST}\n'
            after = before.replace(old + '@' + DIGEST, new + '@' + NEXT)
            changes = POLICY.image_changes('compose/example.yml', before, after, [])
            self.assertEqual(len(changes), 1)
        for prefix in ('FROM', 'DOCKER_MODS:'):
            before = f'{prefix} example/app:latest@{DIGEST}\n'
            self.assertEqual(len(POLICY.image_changes('compose/app/Dockerfile', before,
                                                     before.replace(DIGEST, NEXT), [])), 1)

    def test_major_protected_unpinned_and_unrelated_changes_require_manual(self):
        before = f'    image: example/app:1.2@{DIGEST}\n'
        for path, after, protected in [
                ('compose/app.yml', before.replace('1.2', '2.0'), []),
                ('compose/app.yml', before.replace(DIGEST, NEXT), ['example/app']),
                ('compose/app.yml', before.replace('@' + DIGEST, ''), []),
                ('compose/app.yml', before.replace(DIGEST, NEXT) + 'restart: always\n', []),
                ('README.md', before.replace(DIGEST, NEXT), [])]:
            with self.subTest(path=path, after=after), self.assertRaises(ValueError):
                POLICY.image_changes(path, before, after, protected)

    def test_full_release_range_requires_bot_merge_provenance(self):
        before = f'image: example/app:latest@{DIGEST}'
        after = before.replace(DIGEST, NEXT)

        def git(*args):
            if args[0] == 'rev-parse':
                return 'head' if args[1] == 'HEAD' else 'base'
            if args[0] == 'rev-list':
                return 'head'
            if args[:3] == ('show', '-s', '--format=%P'):
                return 'base'
            if args[0] == 'diff':
                return 'compose/app.yml'
            return before if args[1].startswith('base:') else after

        release = {'draft': False, 'prerelease': False, 'tag_name': 'v1.0.0', 'published_at': '2026-10-12'}
        pr = {'user': {'login': 'renovate[bot]'}, 'merged_at': 'today',
              'base': {'ref': 'main'}, 'merge_commit_sha': 'head'}
        with patch.dict(os.environ, {'EXPECTED_REVISION': 'head'}), \
                patch.object(POLICY, 'git', side_effect=git), patch.object(POLICY.subprocess, 'run') as run:
            run.return_value.returncode = 0
            with patch.object(POLICY, 'api', side_effect=lambda p: [release] if p.startswith('releases') else [pr]):
                self.assertTrue(POLICY.authorize()['eligible'])
                pr['user']['login'] = 'human'
                with self.assertRaisesRegex(ValueError, 'non_renovate'):
                    POLICY.authorize()
                with patch.dict(os.environ, {'EXPECTED_REVISION': 'unexpected'}):
                    with self.assertRaisesRegex(ValueError, 'revision_mismatch'):
                        POLICY.authorize()

    def test_all_protected_packages_are_manual_in_renovate(self):
        config = json.loads((ROOT / 'renovate.json').read_text())
        for package in RUNTIME.POLICY['protected_packages']:
            rules = [r for r in config['packageRules'] if package in r.get('matchPackageNames', [])
                     and 'matchCurrentValue' not in r]
            self.assertTrue(rules)
            self.assertFalse(rules[-1]['automerge'])
        self.assertEqual(config['rebaseWhen'], 'behind-base-branch')
        self.assertEqual(config['automergeStrategy'], 'merge-commit')
        self.assertEqual(config['baseBranchPatterns'], ['main'])


class RoutineRuntimeTests(unittest.TestCase):
    def test_disabled_services_remain_stopped_while_enabled_images_reconcile(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            (state / 'homelab.json').write_text(json.dumps({'current_release': 'v1.0.0'}))
            source = 'compose/platform/logging/compose.yml'
            config = {'services': {name: {'image': 'example/app:1.2.3@' + NEXT,
                                         'container_name': name} for name in ('logging-loki', 'enabled')}}

            def command(*args):
                if args[:2] == ('git', 'rev-parse'):
                    return 'head'
                if args[:2] in (('git', 'ls-files'), ('git', 'diff')):
                    return source
                return ''

            def inspect(*args):
                if args[:2] == ('docker', 'inspect'):
                    return [{'Image': 'old', 'State': {'Status': 'exited' if args[-1] == 'logging-loki' else 'running'},
                             'Config': {'Env': []}, 'HostConfig': {'RestartPolicy': {'Name': 'no'}}}]
                return [{'RepoDigests': ['example/app@' + DIGEST], 'Config': {}}]

            with patch.object(RUNTIME, 'STATE', state), patch.object(RUNTIME, 'command', side_effect=command), \
                    patch.object(RUNTIME, 'compose', return_value=json.dumps(config)), \
                    patch.object(RUNTIME, 'json_command', side_effect=inspect), \
                    patch.object(RUNTIME, 'media_gate'), patch.object(RUNTIME, 'backup_gate'):
                for automatic in (True, False):
                    result = RUNTIME.plan(automatic)
                    self.assertEqual(result['disabled'], ['logging-loki'])
                    self.assertEqual([r['container'] for r in result['services']], ['enabled'])
                config['services'].pop('enabled')
                with patch.object(RUNTIME, 'json_command', return_value=[{'State': {'Status': 'running'}}]):
                    with self.assertRaisesRegex(ValueError, 'disabled_service_is_running'):
                        RUNTIME.plan(False)

    def test_approved_manual_workflow_uses_scoped_apply_health_and_recovery(self):
        document = yaml.safe_load((ROOT / '.github/workflows/deploy.yml').read_text())
        inputs = document['jobs']['deploy']['with']
        for operation in ('check', 'deploy', 'health_check'):
            name = {'check': 'check', 'deploy': 'apply', 'health_check': 'health'}[operation]
            self.assertIn('release-' + name, inputs['privileged_' + operation + '_command'])
        self.assertIn('release-rollback', inputs['privileged_rollback_command'])
        playbook = yaml.safe_load((ROOT / 'ansible/playbooks/homelab-routine.yml').read_text())[0]
        self.assertTrue(playbook['vars']['routine_automatic'])
        for task in (playbook['tasks'][0], playbook['tasks'][2]):
            self.assertIn('--manual', task['ansible.builtin.command']['argv'])

    def transaction(self):
        return {'revision': 'head', 'base': 'v1.0.0', 'rollback_safe': True, 'sources': ['compose/media/plex.yml'],
                'helpers': [], 'configurations': [],
                'services': [{'source': 'compose/media/plex.yml', 'service': name, 'container': name,
                              'target': 'example/app:1.2.3@' + NEXT, 'build': False,
                              'before_id': 'sha256:old', 'before_version': '1.2.3', 'restart': 'no'}
                             for name in ('plex', 'sonarr')]}

    def test_eligible_update_recreates_only_affected_services_in_order(self):
        transaction = self.transaction()
        candidate = [{'Id': 'sha256:new', 'RepoDigests': ['example/app@' + NEXT],
                      'Config': {'Labels': {'org.opencontainers.image.version': '1.2.3'}}}]
        with patch.object(RUNTIME, 'load_transaction', return_value=transaction), patch.object(RUNTIME, 'write'), \
                patch.object(RUNTIME, 'command') as command, patch.object(RUNTIME, 'json_command', return_value=candidate), \
                patch.object(RUNTIME, 'compose') as compose, patch.object(RUNTIME, 'media_gate') as mount, \
                patch.object(RUNTIME, 'verify') as verify:
            RUNTIME.apply(True)
            self.assertEqual([c.args[-1] for c in compose.call_args_list], ['plex', 'sonarr'])
            for call in compose.call_args_list:
                self.assertIn('--no-deps', call.args)
                self.assertIn('--no-build', call.args)
                self.assertIn('--force-recreate', call.args)
            self.assertEqual([c.args[0]['container'] for c in verify.call_args_list], ['plex', 'sonarr'])
            self.assertEqual(mount.call_count, 2)
            self.assertEqual(len([c for c in command.call_args_list if 'pull' in c.args]), 2)
            self.assertTrue(all(row['expected_id'] == 'sha256:new' for row in transaction['services']))

    def test_health_failure_stops_rollout_before_next_service(self):
        transaction = self.transaction()
        candidate = [{'Id': 'new', 'RepoDigests': ['example/app@' + NEXT],
                      'Config': {'Labels': {'org.opencontainers.image.version': '1.2.3'}}}]
        with patch.object(RUNTIME, 'load_transaction', return_value=transaction), patch.object(RUNTIME, 'write'), \
                patch.object(RUNTIME, 'command'), patch.object(RUNTIME, 'json_command', return_value=candidate), \
                patch.object(RUNTIME, 'compose') as compose, patch.object(RUNTIME, 'media_gate'), \
                patch.object(RUNTIME, 'verify', side_effect=ValueError('unhealthy')):
            with self.assertRaises(ValueError):
                RUNTIME.apply(True)
            self.assertEqual(compose.call_count, 1)
            self.assertTrue(transaction['services'][0]['applied'])
            self.assertNotIn('applied', transaction['services'][1])

    def test_unlabelled_image_uses_version_probe_during_apply(self):
        transaction = self.transaction()
        candidate = [{'Id': 'sha256:new', 'RepoDigests': ['example/app@' + NEXT], 'Config': {}}]
        with patch.object(RUNTIME, 'load_transaction', return_value=transaction), patch.object(RUNTIME, 'write'), \
                patch.object(RUNTIME, 'command'), patch.object(RUNTIME, 'json_command', return_value=candidate), \
                patch.object(RUNTIME, 'compose'), patch.object(RUNTIME, 'media_gate'), \
                patch.object(RUNTIME, 'verify'), patch.object(RUNTIME, 'binary_version', return_value='1.2.3') as probe:
            RUNTIME.apply(True)
            self.assertEqual(probe.call_count, 2)
            self.assertEqual(transaction['outcome'], 'success')

    def test_openproject_upgrade_seeds_before_processes_and_blocks_schema_rollback(self):
        transaction = self.transaction()
        for row, name in zip(transaction['services'], ('projects-cron', 'projects-web')):
            row.update(container=name, service=name, before_version='17.7.1',
                       source='compose/productivity/openproject/compose.yml',
                       target='openproject/openproject:17-slim@' + NEXT)
        candidate = [{'Id': 'sha256:new', 'RepoDigests': ['openproject/openproject@' + NEXT],
                      'Config': {'Labels': {'org.opencontainers.image.version': '17.9.1'}}}]
        with patch.object(RUNTIME, 'load_transaction', return_value=transaction), patch.object(RUNTIME, 'write'), \
                patch.object(RUNTIME, 'command'), patch.object(RUNTIME, 'json_command', return_value=candidate), \
                patch.object(RUNTIME, 'compose') as compose, patch.object(RUNTIME, 'media_gate'), \
                patch.object(RUNTIME, 'verify'):
            RUNTIME.apply(False)
            self.assertEqual([c.args[-1] for c in compose.call_args_list],
                             ['projects-seeder', 'projects-cron', 'projects-web'])
            self.assertIn('--no-deps', compose.call_args_list[0].args)
            self.assertFalse(transaction['rollback_safe'])
            self.assertTrue(transaction['openproject_migrated'])
            transaction.pop('openproject_migrated')
            for row in transaction['services']:
                row.pop('applied')
            compose.reset_mock()
            compose.side_effect = ValueError('migration_failed')
            with self.assertRaisesRegex(ValueError, 'migration_failed'):
                RUNTIME.apply(False)
            self.assertEqual(compose.call_count, 1)
            self.assertFalse(transaction['rollback_safe'])
            self.assertTrue(all(not row.get('applied') for row in transaction['services']))

    def test_recovery_uses_retained_image_ids_without_pull(self):
        transaction = self.transaction()
        transaction['services'][0]['applied'] = True
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            snapshot = state / 'rollback-sources' / transaction['services'][0]['source']
            snapshot.parent.mkdir(parents=True)
            snapshot.write_text('services: {}\n')
            record = state / 'routine-update.json'
            record.write_text(json.dumps(transaction))
            with patch.object(RUNTIME, 'STATE', state), patch.object(RUNTIME, 'TRANSACTION', record), \
                    patch.object(RUNTIME, 'command', return_value='head') as command, \
                    patch.object(RUNTIME, 'media_gate'), patch.object(RUNTIME, 'verify') as verify:
                RUNTIME.rollback()
                calls = [c.args for c in command.call_args_list if c.args[:2] == ('docker', 'compose')]
                self.assertEqual(len(calls), 1)
                self.assertIn('--no-deps', calls[0])
                self.assertIn('never', calls[0])
                override = json.loads((state / 'rollback-image.json').read_text())
                self.assertEqual(override['services']['plex']['image'], 'sha256:old')
                verify.assert_called_once_with(transaction['services'][0], recovering=True)
                transaction['rollback_safe'] = False
                record.write_text(json.dumps(transaction))
                with self.assertRaisesRegex(ValueError, 'schema_downgrade'):
                    RUNTIME.rollback()

    def test_migration_unknown_major_and_downgrade_safety(self):
        for before, after in [('1.2.3', '2.0.0'), ('1.2.3', None), ('1.2.3', '1.2.2'), ('4.0.20.3009', '4.0.20.3008')]:
            with self.assertRaises(ValueError):
                RUNTIME.compatibility(before, after, True)
        self.assertFalse(RUNTIME.compatibility('1.2.3', '1.3.0', True))
        self.assertTrue(RUNTIME.compatibility('1.2.3', '1.2.3', True))
        self.assertTrue(RUNTIME.compatibility('v2.11.2', '2.11.2', True))
        self.assertFalse(RUNTIME.compatibility('2.11.2', None, False))
        self.assertFalse(RUNTIME.compatibility('4.0.20.3009-ls132', '4.0.20.3009-ls133', True))
        self.assertEqual(RUNTIME.semver('Linuxserver.io version:- 4.0.20.1-ls123 Build-date:- today'), (4, 0, 20, 1))
        with patch.object(RUNTIME, 'command', return_value='4.108.2 build-id') as command:
            self.assertEqual(RUNTIME.binary_version('code-server'), '4.108.2')
            command.assert_called_with('docker', 'exec', 'code-server', 'code-server', '--version')
            self.assertEqual(RUNTIME.binary_version('code-server', 'approved-image'), '4.108.2')
            command.assert_called_with('docker', 'run', '--rm', '--network', 'none', '--entrypoint',
                                       'code-server', 'approved-image', '--version')

    def test_planner_preserves_unrelated_services_and_media_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            (state / 'homelab.json').write_text(json.dumps({'current_release': 'v1.0.0'}))
            source = 'compose/media/acquisition.yml'
            config = {'services': {name: {'image': 'example/app:1.2.3@' + NEXT,
                                         'container_name': name} for name in ('radarr', 'sonarr')}}
            config['services']['unrelated'] = {'image': 'example/app:1.2.3@' + DIGEST}

            def command(*args):
                if args[:2] == ('git', 'rev-parse'):
                    return 'head'
                if args[:2] in (('git', 'ls-files'), ('git', 'diff')):
                    return source
                return ''

            def inspect(*args):
                if args[:2] == ('docker', 'inspect'):
                    return [{'Image': 'old', 'State': {'Status': 'running' if args[-1] != 'unrelated' else 'exited'},
                             'Config': {'Env': []}, 'HostConfig': {'RestartPolicy': {'Name': 'no'}}}]
                return [{'RepoDigests': ['example/app@' + DIGEST], 'Config': {}}]

            with patch.object(RUNTIME, 'STATE', state), patch.object(RUNTIME, 'command', side_effect=command), \
                    patch.object(RUNTIME, 'compose', return_value=json.dumps(config)), \
                    patch.object(RUNTIME, 'json_command', side_effect=inspect), \
                    patch.object(RUNTIME, 'media_gate') as mount, patch.object(RUNTIME, 'backup_gate') as backup:
                result = RUNTIME.plan(True)
                self.assertEqual([r['container'] for r in result['services']], ['sonarr', 'radarr'])
                self.assertEqual(result['sources'], [source])
                mount.assert_called_once_with(['sonarr', 'radarr'])
                backup.assert_called_once()

    def test_automatic_runtime_rejects_undeployed_manual_release_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            (state / 'homelab.json').write_text(json.dumps({'current_release': 'v1.0.0'}))
            with patch.object(RUNTIME, 'STATE', state), \
                    patch.object(RUNTIME, 'command', return_value='README.md'), \
                    patch.object(RUNTIME, 'compose') as compose:
                with self.assertRaisesRegex(ValueError, 'undeployed_manual_changes'):
                    RUNTIME.plan(True)
                compose.assert_not_called()

    def test_backup_integrity_freshness_and_active_cluster_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            group = root / 'completed'
            group.mkdir()
            now = datetime.datetime.now(datetime.timezone.utc)
            policy = yaml.safe_load((ROOT / 'recovery/backup-policy.yml').read_text())
            policy['off_source_copy_root'] = str(root / 'off-source')
            copy_root = Path(policy['off_source_copy_root'])
            copy_root.mkdir()
            policy_file = root / 'policy.yml'
            policy_file.write_text(yaml.safe_dump(policy))
            entries = []
            for index, source in enumerate(policy['required_sources']):
                artifact = group / str(index)
                artifact.write_bytes(b'age-encryption.org/v1\nfixture-ciphertext')
                entries.append({'source': source, 'artifact': artifact.name, 'format': 'postgres-sql-age',
                                'encryption': {'format': 'age', 'recipient': policy['encryption_recipient']},
                                'size_bytes': artifact.stat().st_size,
                                'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(),
                                'created_at': now.isoformat(), 'completed_at': now.isoformat()})
                if source in policy.get('off_source_copy_sources', []):
                    copied = copy_root / artifact.name
                    copied.write_bytes(artifact.read_bytes())
                    metadata = copied.with_name(copied.name + '.json')
                    metadata.write_text(json.dumps({
                        'artifact': str(copied), 'consumer': 'homelab', 'environment': 'home',
                        'source': source, 'recovery_group': 'completed',
                        'sha256': entries[-1]['sha256'], 'size_bytes': entries[-1]['size_bytes']}))
                    entries[-1]['off_source_copy'] = {
                        'artifact': str(copied), 'metadata': str(metadata),
                        'sha256': entries[-1]['sha256']}
            record = {'schema_version': 1, 'consumer': 'homelab', 'environment': 'home',
                      'postgres_container': 'homelab-postgres',
                      'recovery_group': 'completed', 'completed_at': now.isoformat(), 'created_at': now.isoformat(),
                      'max_age_seconds': 86400, 'databases': [],
                      'required_sources': policy['required_sources'], 'artifacts': entries}
            manifest = group / 'manifest.json'
            manifest.write_text(json.dumps(record))
            pointer = root / 'current.json'
            pointer.write_text(json.dumps({'schema_version': 1, 'manifest': 'completed/manifest.json'}))
            RUNTIME.backup_gate(pointer, now, policy_file)
            for changes in ({'consumer': 'infrastructure'}, {'required_sources': ['openproject', 'other']},
                            {'artifacts': entries[1:]}, {'completed_at': (now - datetime.timedelta(days=2)).isoformat()}):
                manifest.write_text(json.dumps(record | changes))
                with self.assertRaises(ValueError):
                    RUNTIME.backup_gate(pointer, now, policy_file)

    def test_image_health_restart_policy_and_mount_identity_are_enforced(self):
        row = self.transaction()['services'][0] | {'expected_id': 'new'}
        container = {'Image': 'wrong', 'State': {'Status': 'running'},
                     'HostConfig': {'RestartPolicy': {'Name': 'no'}}}
        with patch.object(RUNTIME, 'json_command', return_value=[container]):
            with self.assertRaisesRegex(ValueError, 'image_identity'):
                RUNTIME.verify(row)
            container['Image'] = 'new'
            container['HostConfig']['RestartPolicy']['Name'] = 'always'
            with self.assertRaisesRegex(ValueError, 'restart_policy'):
                RUNTIME.verify(row)
        with patch.object(RUNTIME, 'command', return_value='/dev/sda'):
            with self.assertRaisesRegex(ValueError, 'mount_source'):
                RUNTIME.media_gate(['plex'])
        container['HostConfig']['RestartPolicy']['Name'] = 'no'
        container['NetworkSettings'] = {'Networks': {'logging': {'IPAddress': '10.0.0.2'}}}
        with patch.object(RUNTIME, 'json_command', return_value=[container]), patch.object(RUNTIME, 'endpoint') as endpoint:
            RUNTIME.verify(row | {'container': 'logging-alloy'})
            endpoint.assert_called_once_with('http://10.0.0.2:12345/-/ready')

    def test_openproject_tag_override_cannot_bypass_pin(self):
        services = yaml.safe_load((ROOT / 'compose/productivity/openproject/compose.yml').read_text())['services']
        for service in services.values():
            if service.get('image', '').startswith('openproject/openproject:'):
                self.assertNotIn('${TAG', service['image'])
                self.assertIn('@sha256:', service['image'])

    def test_backup_extension_preserves_existing_schedule_and_cluster_requirement(self):
        tasks = yaml.safe_load((ROOT / 'ansible/roles/backups/tasks/main.yml').read_text())
        self.assertNotIn('cron', str(tasks))
        job = next(task['ansible.builtin.blockinfile'] for task in tasks if 'ansible.builtin.blockinfile' in task)
        self.assertEqual(job['path'], '{{ backups_configuration.schedule.reference }}')
        self.assertIn('sudo -n /usr/local/sbin/homelab-recovery-backup', job['block'])
        installation = next(task['ansible.builtin.copy'] for task in tasks
                            if task.get('ansible.builtin.copy', {}).get('dest') == '/usr/local/sbin/homelab-recovery-backup')
        self.assertEqual(('root', '0700'), (installation['owner'], installation['mode']))
        policy = yaml.safe_load((ROOT / 'ansible/inventory/group_vars/homelab.yml').read_text())['backups_configuration']
        self.assertEqual(policy['postgres']['container'], 'homelab-postgres')
        self.assertIn('grafana', policy['postgres']['required_databases'])
        self.assertFalse(policy['quiesce_authorized'])


if __name__ == '__main__':
    unittest.main()
