#!/usr/bin/env python3
"""Authorize only complete, image-only Renovate ranges; no release/runtime mutation."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = re.compile(r'^(\s*(?:image:|DOCKER_MODS:|FROM)\s+)(\S+)(.*)$', re.M)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def api(path):
    # Homelab is public. Public PR provenance needs no token permission; this
    # keeps shared authorization compatible with existing contents-only callers.
    # https://docs.github.com/en/rest/commits/commits#list-pull-requests-associated-with-a-commit
    headers = {'Accept': 'application/vnd.github+json'}
    if not path.endswith('/pulls'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    request = urllib.request.Request('https://api.github.com/repos/' +
                                    os.environ['GITHUB_REPOSITORY'] + '/' + path,
                                    headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def reference(value):
    value = value.strip('\"\'')
    # Resolve the repository-owned fallback, never an untrusted runtime override.
    value = re.sub(r'\$\{[A-Z_]+:-([^}]+)\}', r'\1', value)
    package, _, tag = value.split('@')[0].partition(':')
    return package, tag, re.findall(r'sha256:[a-f0-9]{64}', value)


def image_changes(path, old, new, protected):
    if not (path.startswith('compose/') and
            (path.endswith(('.yml', '.yaml')) or path.endswith('/Dockerfile'))):
        raise ValueError('non_image_source')
    before, after = list(REFERENCE.finditer(old)), list(REFERENCE.finditer(new))
    normalize = lambda text: REFERENCE.sub(lambda m: m[1] + '<image>' + m[3], text)
    if normalize(old) != normalize(new) or len(before) != len(after):
        raise ValueError('non_image_change')
    changes = []
    for a, b in zip(before, after):
        if a[2] == b[2]:
            continue
        ap, at, ah = reference(a[2])
        bp, bt, bh = reference(b[2])
        if ap != bp or ap in protected or not bh:
            raise ValueError('protected_or_unpinned_image')
        if at != bt:
            av, bv = re.match(r'v?([0-9]+(?:\.[0-9]+){1,3})', at), re.match(r'v?([0-9]+(?:\.[0-9]+){1,3})', bt)
            old_version = tuple(map(int, av[1].split('.'))) if av else ()
            new_version = tuple(map(int, bv[1].split('.'))) if bv else ()
            if not av or not bv or old_version[0] != new_version[0] or new_version < old_version:
                raise ValueError('major_channel_or_downgrade')
        changes.append({'source': path, 'package': bp, 'before': a[2], 'after': b[2]})
    return changes


def authorize():
    head = git('rev-parse', 'HEAD')
    if head != os.environ.get('EXPECTED_REVISION', os.environ.get('GITHUB_SHA', head)):
        raise ValueError('revision_mismatch')
    releases = api('releases?per_page=100')
    bases = []
    for release in releases:
        if release['draft'] or release['prerelease']:
            continue
        tag = release['tag_name']
        revision = git('rev-parse', tag + '^{commit}')
        if revision != head and subprocess.run(['git', 'merge-base', '--is-ancestor', revision, head],
                                               cwd=ROOT, capture_output=True).returncode == 0:
            bases.append((release['published_at'], tag))
    if not bases:
        raise ValueError('no_published_baseline')
    base = max(bases)[1]
    protected = json.loads((ROOT / 'routine-updates.json').read_text())['protected_packages']
    changes = []
    for commit in git('rev-list', '--first-parent', '--reverse', base + '..HEAD').splitlines():
        parents = git('show', '-s', '--format=%P', commit).split()
        if len(parents) != 1:
            raise ValueError('routine_updates_require_squash_commits')
        prs = api('commits/' + commit + '/pulls')
        if not any(p['user']['login'] == 'renovate[bot]' and p['merged_at'] and
                   p['base']['ref'] == 'main' and p['merge_commit_sha'] == commit for p in prs):
            raise ValueError('non_renovate_release_scope')
        files = git('diff', '--name-only', parents[0], commit).splitlines()
        for path in files:
            old = git('show', parents[0] + ':' + path)
            new = git('show', commit + ':' + path)
            changes.extend(image_changes(path, old, new, protected))
    if not changes:
        raise ValueError('no_routine_updates')
    return {'eligible': True, 'revision': head, 'base': base, 'changes': changes}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--authorize', action='store_true')
    parser.add_argument('--classify', action='store_true')
    args = parser.parse_args()
    try:
        result = authorize()
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        reason = str(error) if isinstance(error, ValueError) and re.fullmatch(r'[a-z_]+', str(error)) else 'policy_evidence_unavailable'
        result = {'eligible': False, 'reason': reason}
    print(json.dumps(result))
    if output := os.environ.get('GITHUB_OUTPUT'):
        with open(output, 'a') as stream:
            stream.write('eligible=' + str(result['eligible']).lower() + '\n')
    return 0 if result['eligible'] or args.classify else 1


if __name__ == '__main__':
    raise SystemExit(main())
