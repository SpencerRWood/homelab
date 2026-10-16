// Run with Node 24 and an installed renovate@44.151.2 package directory.
// Exercise Renovate's real extractors, RE2 patterns, and replacement templates.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const renovate = resolve(process.argv[2] ?? 'node_modules/renovate');
const load = (path) => import(pathToFileURL(resolve(renovate, 'dist', path)));
const { extractPackageFile: compose } = await load('modules/manager/docker-compose/extract.js');
const { extractPackageFile: dockerfile } = await load('modules/manager/dockerfile/extract.js');
const { extractPackageFile: regex } = await load('modules/manager/custom/regex/index.js');
const { compile } = await load('util/template/index.js');
const { regEx } = await load('util/regex.js');
const { applyPackageRules } = await load('util/package-rules/index.js');
const config = JSON.parse(readFileSync('renovate.json', 'utf8'));
for (const [packageName, currentValue, updateType, expected] of [
  ['openproject/openproject', '17-slim', 'digest', false],
  ['openproject/openproject', '17.9.2-slim', 'digest', true],
  ['openproject/hocuspocus', '17.9.2', 'digest', true],
  ['openproject/hocuspocus', '17.9.2', 'pinDigest', true],
  ['openproject/hocuspocus', '17.9.1', 'patch', false],
  ['openproject/openproject', '17.9.2-slim', 'minor', false],
  ['openproject/openproject', '17.9.2-slim', 'major', false],
  ['busybox', '1.38', 'digest', false],
  ['pgvector/pgvector', '0.8.7-pg16-bookworm', 'digest', false],
  ['grafana/loki', 'latest', 'digest', true],
]) {
  const resolved = await applyPackageRules({ ...config, datasource: 'docker',
    depName: packageName, packageName, currentValue, updateType });
  assert.equal(resolved.automerge, expected, `${packageName}:${currentValue} ${updateType}`);
}
const [images, caddyFrom, mods] = config.customManagers;
const digest = `sha256:${'a'.repeat(64)}`;
const nextDigest = `sha256:${'b'.repeat(64)}`;
const extract = (content, rule = images) => regex(content, 'fixture.yml', rule)?.deps ?? [];
const render = (dep, value, hash) => compile(images.autoReplaceStringTemplate,
  { ...dep, newValue: value, newDigest: hash }, false);

// Pin insertion, digest refresh, and version changes must retain the override
// variable, registry, tag channel, closing brace, and all repeated occurrences.
for (const [name, tag] of [['grafana/loki', 'latest'], ['openproject/openproject', '17-slim']]) {
  const original = `image: ${name}:\u0024{IMAGE_TAG:-${tag}}`;
  const [dep] = extract(original);
  assert.equal(dep.depName, name);
  assert.equal(dep.currentValue, tag);
  const pinned = render(dep, tag, digest);
  assert.equal(pinned, `image: ${name}:\u0024{IMAGE_TAG:-${tag}@${digest}}`);
  const [pinnedDep] = extract(pinned);
  assert.equal(pinnedDep.currentDigest, digest);
  assert.equal(render(pinnedDep, tag, nextDigest), pinned.replace(digest, nextDigest));
  assert.equal(render(pinnedDep, '18-slim', nextDigest),
    `image: ${name}:\u0024{IMAGE_TAG:-18-slim@${nextDigest}}`);
  assert.equal(extract(`${original}\n${original}`).length, 2);
}
assert.equal(extract('image: busybox:1.38').length, 0);
assert.equal(extract('image: ${EXTERNAL_IMAGE}').length, 0);
assert.equal(extract('image: grafana/loki:${LOKI_IMAGE_TAG}').length, 0);
assert.equal(extract('image: grafana/loki:${LOKI_IMAGE_TAG:-latest@sha256:bad}').length, 0);
const [mod] = extract(readFileSync('compose/books/compose.yml', 'utf8'), mods);
assert.equal(mod.depName, 'linuxserver/mods');
assert.equal(mod.currentValue, 'universal-calibre');
const pinnedMod = compile(mods.autoReplaceStringTemplate,
  { ...mod, newValue: mod.currentValue, newDigest: digest }, false);
assert.equal(pinnedMod, `DOCKER_MODS: linuxserver/mods:universal-calibre@${digest}`);
assert.equal(extract(pinnedMod, mods)[0].currentDigest, digest);
assert.equal(compile(mods.autoReplaceStringTemplate,
  { ...extract(pinnedMod, mods)[0], newValue: mod.currentValue, newDigest: nextDigest }, false),
  pinnedMod.replace(digest, nextDigest));

const files = execFileSync('git', ['ls-files'], { encoding: 'utf8' }).trim().split('\n');
let references = 0;
let customReferences = 0;
for (const file of files.filter((f) => /^compose\/.*\.ya?ml$/.test(f))) {
  const content = readFileSync(file, 'utf8');
  const standard = compose(content, file, config)?.deps.filter((d) => !d.skipReason) ?? [];
  const custom = extract(content);
  for (const dep of custom) {
    assert(!standard.some((d) => d.replaceString === dep.replaceString),
      `Duplicate manager ownership in ${file}: ${dep.replaceString}`);
  }
  for (const match of content.matchAll(/^\s*image:\s*(\S+)/gm)) {
    references++;
    const image = match[1];
    const owners = [...standard, ...custom].filter((d) => d.replaceString?.includes(image));
    assert.equal(owners.length > 0 || image.startsWith('local/caddy-cloudflare:') ||
      image.startsWith('code-server-codex:'), true, `Unmanaged image in ${file}: ${image}`);
  }
  customReferences += custom.length;
}
const mediaPattern = config['docker-compose'].managerFilePatterns[0].slice(1, -1);
assert(regEx(mediaPattern).test('compose/media/plex.yml'));
assert(regEx(mediaPattern).test('compose/media/acquisition.yml'));
assert(!regEx(mediaPattern).test('ansible/inventory/homelab.yml'));
assert(config.enabledManagers.includes('dockerfile'));
const bases = dockerfile(readFileSync('compose/platform/caddy/Dockerfile', 'utf8'), '', config).deps;
assert.equal(bases.length, 2);
assert(bases[0].currentValue.endsWith('-builder'));
assert(bases[1].currentValue.endsWith('-alpine'));
assert.equal(bases[0].currentValue.replace(/-builder$/, ''),
  bases[1].currentValue.replace(/-alpine$/, ''));
const caddyDockerfile = readFileSync('compose/platform/caddy/Dockerfile', 'utf8');
const managedBases = extract(caddyDockerfile, caddyFrom);
assert.deepEqual(managedBases.map((d) => d.currentValue), bases.map((d) => d.currentValue));
for (const dep of managedBases) {
  const pinned = compile(caddyFrom.autoReplaceStringTemplate,
    { ...dep, newValue: dep.currentValue, newDigest: digest }, false);
  assert.equal(pinned, `FROM caddy:\u0024{CADDY_VERSION}-${dep.depType}@${digest}`);
  const content = caddyDockerfile.replace(dep.replaceString, pinned);
  const [pinnedDep] = extract(content, caddyFrom).filter((d) => d.depType === dep.depType);
  assert.equal(pinnedDep.currentDigest, digest);
  assert.equal(compile(caddyFrom.autoReplaceStringTemplate,
    { ...pinnedDep, newValue: dep.currentValue, newDigest: nextDigest }, false),
  pinned.replace(digest, nextDigest));
}
assert.equal(dockerfile(readFileSync('compose/platform/code-server/Dockerfile', 'utf8'), '', config)
  .deps.filter((d) => d.datasource === 'docker').length, 1);
const major = config.packageRules.findLast((r) => r.matchUpdateTypes?.includes('major'));
const database = config.packageRules.findLast((r) => r.matchPackageNames?.includes('pgvector/pgvector'));
assert.equal(config.packageRules.find((r) => r.matchPackageNames?.includes('caddy') &&
  r.matchUpdateTypes?.includes('patch')).enabled, false);
assert.equal(major.automerge, false);
assert.equal(database.automerge, false);
assert(config.packageRules.indexOf(major) > config.packageRules.findIndex((r) => r.automerge === true));
assert(config.packageRules.indexOf(database) > config.packageRules.findIndex((r) => r.automerge === true));
console.log(JSON.stringify({ passed: true, composeImageReferences: references, customReferences,
  dockerfileImageReferences: 3, tested: ['extraction', 'pin insertion', 'digest refresh',
    'version replacement', 'duplicate ownership', 'file matching', 'manual review rules'] }));
