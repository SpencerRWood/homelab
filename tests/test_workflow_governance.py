"""Ensure validation, publication and rollback require distinct authority."""

from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1] / '.github/workflows'


class WorkflowGovernanceTests(unittest.TestCase):
    def test_validated_main_merges_can_publish_and_deploy(self):
        release = yaml.safe_load((ROOT / 'release.yml').read_text())
        triggers = release.get('on', release.get(True))
        self.assertEqual(set(triggers), {'workflow_dispatch', 'push'})
        self.assertFalse(triggers['workflow_dispatch']['inputs']['release_approved']['default'])
        self.assertEqual(set(release['jobs']), {'release', 'deploy'})
        job = release['jobs']['release']
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
        self.assertEqual(deployment['if'].strip(), "github.event_name == 'push'")
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
        self.assertEqual(triggers['push']['branches'], ['**'])
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
