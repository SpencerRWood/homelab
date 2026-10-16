"""Ensure validation, publication and rollback require distinct authority."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1] / '.github/workflows'


class WorkflowGovernanceTests(unittest.TestCase):
    def test_backup_integration_gate_fails_closed_without_deploying_other_revisions(self):
        release = yaml.safe_load((ROOT / 'release.yml').read_text())
        scope = release['jobs']['delivery-scope']
        self.assertEqual(scope['permissions'], {'contents': 'read', 'pull-requests': 'read'})
        command = scope['steps'][0]['run']
        revision = 'a' * 40
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            gh = directory / 'gh'
            gh.write_text('#!/bin/sh\n[ "$1" = api ] || exit 2\n'
                          'case "$2" in\n'
                          'repos/example/homelab/pulls/76) printf "%s\\n" "$TEST_MERGED_REVISION"; exit "$TEST_API_EXIT";;\n'
                          'repos/example/homelab/commits/*/pulls) printf "%s\\n" "$TEST_RECOVERY_INTEGRATION"; exit "$TEST_RECOVERY_EXIT";;\n'
                          '*) exit 2;;\nesac\n')
            gh.chmod(0o700)
            output = directory / 'output'
            for merged, api_exit, event, recovery, recovery_exit, expected in [
                    ('pending', '0', 'push', '0', '0', 'false'),
                    (revision, '0', 'push', '0', '0', 'false'),
                    ('b' * 40, '0', 'push', '0', '0', 'true'),
                    ('b' * 40, '0', 'push', '1', '0', 'false'),
                    ('b' * 40, '0', 'push', '2', '0', None),
                    ('b' * 40, '0', 'push', '', '1', None),
                    ('null', '0', 'push', '0', '0', None),
                    ('', '1', 'push', '0', '0', None),
                    ('', '1', 'workflow_dispatch', '0', '0', 'true')]:
                with self.subTest(merged=merged, api_exit=api_exit, event=event):
                    output.write_text('')
                    result = subprocess.run(['bash', '-c', command], capture_output=True, text=True,
                                            env=os.environ | {
                                                'PATH': str(directory) + os.pathsep + os.environ['PATH'],
                                                'GH_REPO': 'example/homelab', 'EVENT_NAME': event,
                                                'REVISION': revision, 'GITHUB_OUTPUT': str(output),
                                                'TEST_MERGED_REVISION': merged, 'TEST_API_EXIT': api_exit,
                                                'TEST_RECOVERY_INTEGRATION': recovery,
                                                'TEST_RECOVERY_EXIT': recovery_exit})
                    if expected is None:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertEqual(output.read_text(), '')
                    else:
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(output.read_text(), f'automatic_delivery={expected}\n')

    def test_validated_main_merges_can_publish_and_deploy(self):
        release = yaml.safe_load((ROOT / 'release.yml').read_text())
        triggers = release.get('on', release.get(True))
        self.assertEqual(set(triggers), {'workflow_dispatch', 'push'})
        self.assertFalse(triggers['workflow_dispatch']['inputs']['release_approved']['default'])
        self.assertEqual(set(release['jobs']), {'delivery-scope', 'release', 'deploy'})
        job = release['jobs']['release']
        self.assertEqual(job['needs'], 'delivery-scope')
        self.assertIn("needs.delivery-scope.outputs.automatic_delivery == 'true'", job['if'])
        self.assertIn("github.ref == 'refs/heads/main'", job['if'])
        self.assertIn("github.event_name == 'workflow_dispatch'", job['if'])
        self.assertIn('inputs.release_approved == true', job['if'])
        self.assertTrue(job['with']['require_approval'])
        self.assertEqual(job['with']['approved'], '${{ inputs.release_approved == true }}')
        self.assertIn("github.event_name == 'push'", job['if'])
        self.assertNotIn('eligible', job['if'])
        self.assertIn('scripts/main-deployment-policy.py', job['with']['automatic_policy_command'])
        deployment = release['jobs']['deploy']
        self.assertEqual(deployment['needs'], 'release')
        self.assertIn("github.ref == 'refs/heads/main'", deployment['if'])
        self.assertIn("github.event_name == 'push'", deployment['if'])
        self.assertEqual(deployment['with']['ref'], '${{ needs.release.outputs.release_tag || github.sha }}')
        self.assertTrue(deployment['with']['automatic'])

    def test_main_deployment_and_explicit_dispatch_use_scoped_recovery(self):
        deploy = yaml.safe_load((ROOT / 'deploy.yml').read_text())
        triggers = deploy.get('on', deploy.get(True))
        self.assertEqual(set(triggers), {'workflow_dispatch', 'workflow_call'})
        for trigger in triggers.values():
            self.assertFalse(trigger['inputs']['deployment_approved']['default'])
        self.assertIn('release', triggers['workflow_dispatch']['inputs'])
        for job in deploy['jobs'].values():
            self.assertIn("github.ref == 'refs/heads/main'", job['if'])
            self.assertIn("github.event_name == 'workflow_dispatch'", job['if'])
            self.assertIn('inputs.deployment_approved == true', job['if'])
        job = next(job for job in deploy['jobs'].values() if 'deploy-ansible' in job.get('uses', ''))
        self.assertTrue(job['with']['require_approval'])
        self.assertEqual(job['with']['approved'], '${{ inputs.deployment_approved }}')
        self.assertIn('release-apply', job['with']['privileged_deploy_command'])
        self.assertIn('release-rollback', job['with']['privileged_rollback_command'])

    def test_pushes_and_prs_validate_without_publishing_authority(self):
        validate = yaml.safe_load((ROOT / 'validate.yml').read_text())
        triggers = validate.get('on', validate.get(True))
        self.assertEqual(set(triggers), {'push', 'pull_request'})
        self.assertEqual(triggers['push']['branches'], ['development'])
        self.assertEqual(triggers['pull_request']['branches'], ['development', 'main'])
        self.assertEqual(validate['permissions']['contents'], 'read')
        for job in validate['jobs'].values():
            self.assertIn('/validate.yml@', job['uses'])

    def test_recovery_rollback_cannot_apply_from_automatic_events(self):
        rollback = yaml.safe_load((ROOT / 'rollback.yml').read_text())
        triggers = rollback.get('on', rollback.get(True))
        self.assertEqual(set(triggers), {'workflow_call', 'workflow_dispatch'})
        for trigger in triggers.values():
            self.assertFalse(trigger['inputs']['apply']['default'])
        job = rollback['jobs']['rollback']
        self.assertIn('inputs.apply != true', job['if'])
        self.assertIn("github.event_name == 'workflow_dispatch'", job['if'])
        self.assertIn("github.ref == 'refs/heads/main'", job['if'])
        self.assertIn('self-hosted', job['runs-on'])
        self.assertTrue(any('scripts/rollback.py' in step.get('run', '') for step in job['steps']))


if __name__ == '__main__':
    unittest.main()
