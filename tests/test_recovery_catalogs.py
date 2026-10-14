"""Resolved recovery requirements retain all declared Compose dependencies."""
import json
from pathlib import Path
import re
import unittest
import yaml

ROOT = Path(__file__).parents[1]


def images(value):
    if isinstance(value, dict):
        return ([value['image']] if isinstance(value.get('image'), str) else []) + [image for child in value.values() for image in images(child)]
    if isinstance(value, list):
        return [image for child in value for image in images(child)]
    return []


class RecoveryCatalogTests(unittest.TestCase):
    def test_every_compose_image_has_exact_registry_or_explicit_build_requirement(self):
        catalog = json.loads((ROOT / 'recovery/artifacts.v1.json').read_text())['references']
        for file in (ROOT / 'compose').rglob('*.yml'):
            for image in images(yaml.safe_load(file.read_text())):
                resolved = re.sub(r'\$\{[^}]+:-([^}]+)\}', r'\1', image)
                if resolved.startswith('local/caddy-cloudflare:'):
                    self.assertTrue(any('/homelab-caddy/' in reference for reference in catalog))
                elif resolved.startswith('code-server-codex:'):
                    self.assertTrue(any('/homelab-code-server/' in reference for reference in catalog))
                else:
                    self.assertIn('oci://' + resolved, catalog)
        for reference in catalog:
            if reference.startswith('oci://'):
                self.assertRegex(reference, r'@sha256:[0-9a-f]{64}$')
            else:
                self.assertRegex(reference, r'^image-archive:///mnt/wood-server-nas/backup_server/swood-server/infrastructure-dev/image-artifacts/homelab-(caddy|code-server)/[0-9a-f]{64}/manifest\.json$')
        self.assertEqual(len(catalog), len(set(catalog)))


if __name__ == '__main__':
    unittest.main()
