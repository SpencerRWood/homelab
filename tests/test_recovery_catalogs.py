"""Canonical image updates retain exact recovery requirements without metadata edits."""
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('catalog_recovery', ROOT / 'scripts/recovery.py')
RECOVERY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RECOVERY)


class RecoveryCatalogTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        for name in ('compose', 'recovery'):
            shutil.copytree(ROOT / name, self.root / name)

    def references(self):
        with patch.object(RECOVERY, 'clean_revision', return_value='a' * 40):
            manifest, _ = RECOVERY.manifest(self.root)
        return [d['reference'] for d in manifest['targets'][0]['required_dependencies']
                if d['kind'] == 'artifact']

    def test_every_compose_image_retains_exact_identity_and_local_build_evidence(self):
        references = self.references()
        expected = set()
        builds = json.loads((self.root / 'recovery/build-artifacts.v1.json').read_text())['images']
        for file in (self.root / 'compose').rglob('*.yml'):
            for service in yaml.safe_load(file.read_text())['services'].values():
                image = service['image']
                image = re.sub(r'\$\{[^}]+:-([^}]+)\}', r'\1', image)
                expected.add(builds[image.split(':')[0]] if 'build' in service else 'oci://' + image)
        self.assertEqual(set(references), expected)
        self.assertEqual(len(references), len(expected))
        self.assertEqual(references, self.references())

    def test_future_digest_and_patch_updates_need_no_recovery_edits(self):
        file = self.root / 'compose/productivity/openproject/compose.yml'
        original = file.read_text()
        before = self.references()
        for package, tag in [('openproject/openproject', '17-slim'),
                             ('openproject/hocuspocus', '17.9.2')]:
            document = yaml.safe_load(original)
            old = next(s['image'] for s in document['services'].values()
                       if s['image'].startswith(package + ':'))
            new = package + ':' + tag + '@sha256:' + 'b' * 64
            file.write_text(original.replace(old, new))
            after = self.references()
            self.assertIn('oci://' + new, after)
            self.assertNotIn('oci://' + old, after)
            self.assertEqual(len(before), len(after))

    def test_defaults_are_canonical_and_environment_cannot_override_identity(self):
        file = self.root / 'compose/productivity/openproject/compose.yml'
        original = file.read_text()
        image = yaml.safe_load(original)['services']['projects-hocuspocus']['image']
        file.write_text(original.replace(image, 'openproject/hocuspocus:${TEST_IMAGE:-' + image.split(':', 1)[1] + '}'))
        with patch.dict('os.environ', {'TEST_IMAGE': 'untrusted:latest'}):
            self.assertIn('oci://' + image, self.references())

    def test_unpinned_unresolved_missing_and_unknown_builds_fail_closed(self):
        file = self.root / 'compose/productivity/openproject/compose.yml'
        original = yaml.safe_load(file.read_text())
        for value in ('example/app:latest', 'example/app@sha256:bad', '${EXTERNAL_IMAGE}', None):
            document = yaml.safe_load(yaml.safe_dump(original))
            document['services']['projects-hocuspocus']['image'] = value
            file.write_text(yaml.safe_dump(document))
            with self.subTest(value=value), self.assertRaises(RECOVERY.InvalidInput):
                self.references()
        document['services']['projects-hocuspocus'] = {'build': '.', 'image': 'unknown:latest'}
        file.write_text(yaml.safe_dump(document))
        with self.assertRaises(KeyError):
            self.references()

    def test_local_build_artifact_cannot_float(self):
        file = self.root / 'recovery/build-artifacts.v1.json'
        document = json.loads(file.read_text())
        document['images']['local/caddy-cloudflare'] = 'oci://caddy:latest'
        file.write_text(json.dumps(document))
        with self.assertRaises(RECOVERY.InvalidInput):
            self.references()


if __name__ == '__main__':
    unittest.main()
