"""Exercise init-only deployment selection, persistence and failure boundaries."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_routine_updates import DIGEST, NEXT, RUNTIME


class InitReconciliationTests(unittest.TestCase):
    def containers(self, disabled=False):
        return {'Image': 'old', 'Config': {'Env': []},
                'State': {'Status': 'exited' if disabled else 'running', 'ExitCode': 0},
                'HostConfig': {'RestartPolicy': {'Name': 'no'}}}

    def helper(self, deferred=False):
        return {'source': 'compose/productivity/vikunja/compose.yml', 'service': 'vikunja-init',
                'container': 'vikunja-init', 'target': 'busybox:1.38@' + NEXT,
                'before_id': 'old-helper', 'deferred': deferred,
                'consumer': {'container': 'vikunja', 'before_id': 'old', 'expected_id': 'old', 'restart': 'no'}}

    def test_init_only_change_selects_config_when_application_image_is_unchanged(self):
        for disabled in (False, True):
            with self.subTest(disabled=disabled), tempfile.TemporaryDirectory() as tmp:
                state = Path(tmp)
                (state / 'homelab.json').write_text(json.dumps({'current_release': 'v1'}))
                service = 'code-server-init' if disabled else 'vikunja-init'
                source, consumer, _ = RUNTIME.INIT_HELPERS[service]
                config = {'services': {
                    service: {'image': 'busybox:1.38@' + NEXT, 'command': ['sh', '-c',
                              'chown -R 1000:1000 /home/coder /workspace' if disabled else
                              'chown -R 1000:0 /db /files']},
                    consumer: {'image': 'example/app:1.2.3@' + DIGEST, 'container_name': consumer}}}

                def command(*args):
                    if args[:2] == ('git', 'rev-parse'):
                        return 'head'
                    if args[:2] in (('git', 'ls-files'), ('git', 'diff')):
                        return source
                    if args[:2] == ('git', 'show'):
                        return json.dumps({'services': {service: {'image': 'busybox:1.38@' + DIGEST}}})
                    return ''

                def inspect(*args):
                    if args[:2] == ('docker', 'inspect'):
                        return [self.containers(disabled or args[-1] == service)]
                    return [{'RepoDigests': ['example/app@' + DIGEST], 'Config': {}}]

                with patch.object(RUNTIME, 'STATE', state), patch.object(RUNTIME, 'command', side_effect=command), \
                        patch.object(RUNTIME, 'compose', return_value=json.dumps(config)), \
                        patch.object(RUNTIME, 'json_command', side_effect=inspect), \
                        patch.object(RUNTIME, 'backup_gate') as backup:
                    result = RUNTIME.plan(False)
                    self.assertEqual(result['sources'], [source])
                    self.assertEqual(result['services'], [])
                    self.assertEqual(result['helpers'][0]['deferred'], disabled)
                    self.assertEqual(result['configurations'][0]['sha256'],
                                     hashlib.sha256((RUNTIME.ROOT / source).read_bytes()).hexdigest())
                    self.assertEqual(backup.call_count, 0 if disabled else 1)
                    config['services'][service]['command'][2] = 'rm -rf /files'
                    with patch.object(RUNTIME, 'compose', return_value=json.dumps(config)):
                        with self.assertRaisesRegex(ValueError, 'unsupported_init_helper_command'):
                            RUNTIME.plan(False)

    def test_protected_helper_requires_manual_runtime_approval(self):
        row = self.helper()
        config = {'services': {'vikunja-init': {'image': row['target']}}}
        with patch.object(RUNTIME, 'command', return_value=json.dumps(
                {'services': {'vikunja-init': {'image': 'busybox:1.38@' + DIGEST}}})):
            with self.assertRaisesRegex(ValueError, 'protected_service_requires_manual_approval'):
                RUNTIME.init_helpers(row['source'], config, 'v1', True)

    def test_prepare_saves_actual_configuration_before_copy_and_apply_rejects_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = 'compose/example.yml'
            checkout, canonical, state = [root / name for name in ('checkout', 'canonical', 'state')]
            for path in (checkout / source, canonical / source):
                path.parent.mkdir(parents=True)
            state.mkdir()
            (checkout / source).write_text('new')
            (canonical / source).write_text('actual old')
            transaction = {'sources': [source], 'configurations': [
                {'source': source, 'sha256': hashlib.sha256(b'new').hexdigest()}]}
            with patch.object(RUNTIME, 'ROOT', checkout), patch.object(RUNTIME, 'CANONICAL', canonical), \
                    patch.object(RUNTIME, 'STATE', state), patch.object(RUNTIME, 'TRANSACTION', state / 'transaction'), \
                    patch.object(RUNTIME, 'plan', return_value=transaction):
                RUNTIME.prepare(False)
                self.assertEqual((state / 'rollback-sources' / source).read_text(), 'actual old')
                with self.assertRaisesRegex(ValueError, 'canonical_configuration_mismatch'):
                    RUNTIME.verify_configurations(transaction)
                (canonical / source).write_text('new')
                RUNTIME.verify_configurations(transaction)
                (checkout / source).write_text('unexpected')
                with self.assertRaisesRegex(ValueError, 'configuration_evidence_mismatch'):
                    RUNTIME.verify_configurations(transaction)

    def test_apply_rejects_stale_revision_or_changed_approval_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / 'transaction.json'
            record.write_text(json.dumps({'revision': 'approved', 'automatic': False}))
            with patch.object(RUNTIME, 'TRANSACTION', record), \
                    patch.object(RUNTIME, 'command', return_value='different'):
                with self.assertRaisesRegex(ValueError, 'apply_evidence_revision_or_approval_mismatch'):
                    RUNTIME.load_transaction(False)
            with patch.object(RUNTIME, 'TRANSACTION', record), \
                    patch.object(RUNTIME, 'command', return_value='approved'):
                with self.assertRaisesRegex(ValueError, 'apply_evidence_revision_or_approval_mismatch'):
                    RUNTIME.load_transaction(True)

    def test_helper_executes_without_dependencies_and_records_exact_image_and_exit(self):
        row = self.helper()
        transaction = {'revision': 'head', 'helpers': [row], 'rollback_safe': True}
        candidate = [{'Id': 'new-helper', 'RepoDigests': ['busybox@' + NEXT]}]
        with patch.object(RUNTIME, 'backup_gate') as backup, patch.object(RUNTIME, 'verify'), \
                patch.object(RUNTIME, 'command'), patch.object(RUNTIME, 'json_command', return_value=candidate), \
                patch.object(RUNTIME, 'write') as write, patch.object(RUNTIME, 'verify_helper'), \
                patch.object(RUNTIME, 'compose') as compose:
            RUNTIME.apply_helpers(transaction)
            backup.assert_called_once()
            self.assertEqual(row['expected_id'], 'new-helper')
            self.assertEqual(row['outcome'], 'completed')
            self.assertFalse(transaction['rollback_safe'])
            self.assertTrue(row['attempted'])
            self.assertGreaterEqual(write.call_count, 2)
            self.assertIn('--no-deps', compose.call_args.args)
            self.assertIn('--exit-code-from', compose.call_args.args)
            self.assertEqual(compose.call_args.args[-1], 'vikunja-init')

    def test_disabled_helper_is_deferred_without_pull_or_execution(self):
        row = self.helper(True)
        with patch.object(RUNTIME, 'json_command', return_value=[self.containers(True)]), \
                patch.object(RUNTIME, 'write'), patch.object(RUNTIME, 'command') as command, \
                patch.object(RUNTIME, 'compose') as compose, patch.object(RUNTIME, 'backup_gate') as backup:
            RUNTIME.apply_helpers({'helpers': [row]})
            self.assertEqual(row['outcome'], 'deferred_disabled_consumer')
            command.assert_not_called()
            compose.assert_not_called()
            backup.assert_not_called()

    def test_failed_or_wrong_image_helper_cannot_pass_health_or_automatic_recovery(self):
        row = self.helper() | {'expected_id': 'new-helper'}
        container = self.containers(True) | {'Image': 'new-helper', 'Config': {'Image': row['target']}}
        with patch.object(RUNTIME, 'json_command', return_value=[container]), patch.object(RUNTIME, 'verify'):
            RUNTIME.verify_helper(row)
            for change in ({'State': {'Status': 'exited', 'ExitCode': 1}}, {'Image': 'wrong'},
                           {'State': {'Status': 'running', 'ExitCode': 0}}):
                with patch.object(RUNTIME, 'json_command', return_value=[container | change]):
                    with self.assertRaises(ValueError):
                        RUNTIME.verify_helper(row)
        transaction = {'revision': 'head', 'helpers': [row], 'rollback_safe': True}
        with patch.object(RUNTIME, 'backup_gate'), patch.object(RUNTIME, 'verify'), \
                patch.object(RUNTIME, 'command'), patch.object(RUNTIME, 'json_command', return_value=[
                    {'Id': 'new-helper', 'RepoDigests': ['busybox@' + NEXT]}]), \
                patch.object(RUNTIME, 'write'), \
                patch.object(RUNTIME, 'compose', side_effect=ValueError('helper_failed')):
            with self.assertRaisesRegex(ValueError, 'helper_failed'):
                RUNTIME.apply_helpers(transaction)
            self.assertTrue(row['attempted'])
            self.assertFalse(transaction['rollback_safe'])
            with patch.object(RUNTIME.TRANSACTION.__class__, 'read_text', return_value=json.dumps(transaction)):
                with self.assertRaisesRegex(ValueError, 'init_permission_recovery_requires_manual_review'):
                    RUNTIME.rollback()


if __name__ == '__main__':
    unittest.main()
