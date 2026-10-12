#!/usr/bin/env python3
"""Authorize the exact main push covered by the repository's delivery policy."""
import json
import os
import subprocess


def authorize():
    if os.environ.get('GITHUB_EVENT_NAME') != 'push' or os.environ.get('GITHUB_REF') != 'refs/heads/main':
        raise ValueError('deployment_requires_main_push')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    if head != os.environ.get('GITHUB_SHA') or head != os.environ.get('EXPECTED_REVISION'):
        raise ValueError('deployment_revision_mismatch')
    return {'authorized': True, 'revision': head}


if __name__ == '__main__':
    try:
        print(json.dumps(authorize()))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        reason = str(error) if isinstance(error, ValueError) else 'deployment_evidence_unavailable'
        print(json.dumps({'authorized': False, 'reason': reason}))
        raise SystemExit(1)
