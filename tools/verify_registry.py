# SPDX-License-Identifier: MIT
"""Qualify the real CLI install path and render the installed component kits."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import threading
import urllib.request
import venv
import zipfile

VERSIONS = {'stable': '2.5.29', 'alpha': '2.6.0a4'}
TEMPLATES = {'python-components', 'component-showcase'}
PUBLIC_REGISTRY = 'https://raw.githubusercontent.com/fullbleed-engine/fullbleed-manifest/master/manifest.json'


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def download(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Fullbleed-template-verification'})
    with urllib.request.urlopen(request, timeout=45) as response:
        assert response.status == 200
        return response.read()


@contextmanager
def registry_server(directory):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def verify(args):
    out = args.out.absolute()
    out.mkdir(parents=True, exist_ok=False)
    logs = out / 'logs'
    logs.mkdir()
    environment = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}

    def command(label, argv, *, cwd=None, expected=0, timeout=300):
        result = subprocess.run(list(map(str, argv)), cwd=cwd, env=environment,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        (logs / (label + '.stdout')).write_bytes(result.stdout)
        (logs / (label + '.stderr')).write_bytes(result.stderr)
        if expected is None:
            assert result.returncode != 0, label + ': expected rejection'
        else:
            assert result.returncode == expected, label + ': ' + result.stderr.decode('utf-8', errors='replace')[-2000:]
        return result.stdout.decode('utf-8')

    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    assert manifest['schema'] == 'fullbleed.template_registry.v1'
    assert len(manifest['templates']) == len(TEMPLATES)
    assert {item['id'] for item in manifest['templates']} == TEMPLATES
    templates = {item['id']: item for item in manifest['templates']}
    releases = {}
    archives = out / 'archives'
    archives.mkdir()
    expected_files = {}
    for ident, template in templates.items():
        assert len({release['version'] for release in template['releases']}) == len(template['releases'])
        release = next(release for release in template['releases'] if release['version'] == template['latest'])
        assert release['experimental'] and not release['deprecated']
        assert release['fullbleed_version_range'] == '==2.6.0a4'
        archive = release['archive']
        assert archive['format'] == 'zip'
        assert re.fullmatch(r'[0-9a-f]{64}', archive['sha256'])
        assert re.fullmatch(r'https://raw\.githubusercontent\.com/fullbleed-engine/docs/[0-9a-f]{40}/docs/assets/[a-z0-9-]+/project\.zip', archive['url'])
        data = download(archive['url'])
        assert len(data) == archive['size_bytes'] and sha256(data).hexdigest() == archive['sha256']
        local_archive = archives / (ident + '.zip')
        local_archive.write_bytes(data)
        prefix = archive['root_dir'] + '/'
        files = {}
        with zipfile.ZipFile(local_archive) as contents:
            assert contents.testzip() is None
            for member in contents.infolist():
                if member.is_dir():
                    continue
                assert member.filename.startswith(prefix)
                name = member.filename[len(prefix):]
                parts = PurePosixPath(name)
                assert name and not parts.is_absolute() and '..' not in parts.parts and '\\' not in name and ':' not in name
                assert not stat.S_ISLNK(member.external_attr >> 16) and name not in files
                files[name] = sha256(contents.read(member)).hexdigest()
            assert contents.read(prefix + 'requirements.txt').decode().strip() == 'fullbleed==2.6.0a4'
        assert all(value in files for value in release['entrypoints'].values())
        releases[ident], expected_files[ident] = release, files

    runtimes = {}
    for lane in VERSIONS:
        supplied = getattr(args, lane + '_python')
        if supplied:
            # Preserve a virtualenv launcher instead of following its Linux symlink.
            python = supplied.absolute()
        else:
            directory = out / ('runtime-' + lane)
            venv.EnvBuilder(with_pip=True).create(directory)
            python = directory / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            packages = ['fullbleed==' + VERSIONS[lane]]
            if lane == 'alpha':
                packages.append('pypdf==6.19.0')
            command(lane + '-install', [python, '-m', 'pip', 'install', '--only-binary=:all:', *packages], timeout=600)
        actual = json.loads(command(lane + '-version', [python, '-I', '-c', 'import sys,json;from importlib.metadata import version;print(json.dumps({"fullbleed":version("fullbleed"),"python":sys.version.split()[0]}))']))
        assert actual['fullbleed'] == VERSIONS[lane]
        runtimes[lane] = python

    registry_dir = out / 'registry'
    registry_dir.mkdir()
    save(registry_dir / 'manifest.json', manifest)
    broken = json.loads(json.dumps(manifest))
    broken['templates'][0]['releases'][0]['archive']['sha256'] = '0' * 64
    save(registry_dir / 'checksum-mismatch.json', broken)
    checks = []
    with registry_server(registry_dir) as server:
        registry = None if args.default_registry else args.registry_url or server + '/manifest.json'
        if args.default_registry or args.registry_url:
            assert json.loads(download(registry or PUBLIC_REGISTRY)) == manifest, 'Published manifest differs from the candidate'

        def cli(label, lane, *argv, selected_registry=registry, expected=0):
            arguments = [runtimes[lane], '-I', '-m', 'fullbleed_cli', 'new', *argv]
            if selected_registry:
                arguments.extend(['--registry', selected_registry])
            arguments.append('--json')
            return json.loads(command(label, arguments, expected=expected))

        for lane in VERSIONS:
            listed = cli(lane + '-list', lane, 'list')
            searched = cli(lane + '-search', lane, 'search', 'components')
            assert listed['ok'] and searched['ok']
            assert {item['id'] for item in listed['templates']} == TEMPLATES
            assert {item['id'] for item in searched['templates']} == TEMPLATES
            for ident, release in releases.items():
                target = out / lane / ident
                dry = cli(lane + '-' + ident + '-dry', lane, 'remote', ident, str(target), '--version', release['version'], '--dry-run')
                assert dry['ok'] and dry['dry_run'] and not target.exists()
                assert dry['version'] == release['version'] and dry['archive']['sha256'] == release['archive']['sha256']
                result = cli(lane + '-' + ident + '-install', lane, 'remote', ident, str(target), '--version', release['version'])
                assert result['ok'] and not result['dry_run']
                assert result['version'] == release['version'] and result['entrypoints'] == release['entrypoints']
                actual = {path.relative_to(target).as_posix(): sha256(path.read_bytes()).hexdigest() for path in target.rglob('*') if path.is_file()}
                assert actual == expected_files[ident] and result['files_written'] == len(actual)
                checks.append({'lane': lane, 'template': ident, 'version': result['version'], 'files_identical': len(actual), 'archive_sha256': release['archive']['sha256']})

            sentinel = out / lane / 'existing-project'
            sentinel.mkdir()
            (sentinel / 'keep.txt').write_bytes(b'Existing author work.\n')
            rejected = cli(lane + '-existing-target', lane, 'remote', 'python-components', str(sentinel), expected=None)
            assert rejected['code'] == 'NEW_REMOTE_FAILED' and not rejected['ok']
            assert {path.name: path.read_bytes() for path in sentinel.iterdir()} == {'keep.txt': b'Existing author work.\n'}
            rejected = cli(lane + '-checksum', lane, 'remote', broken['templates'][0]['id'], str(sentinel),
                           selected_registry=server + '/checksum-mismatch.json', expected=None)
            assert rejected['code'] == 'NEW_REMOTE_FAILED' and 'sha256 mismatch' in rejected['message']
            assert {path.name: path.read_bytes() for path in sentinel.iterdir()} == {'keep.txt': b'Existing author work.\n'}
            print(json.dumps({'lane': lane, 'installs': len(TEMPLATES), 'existing_files_preserved': True, 'checksum_rejected': True}), flush=True)

    alpha = runtimes['alpha']
    starter = out / 'alpha/python-components'
    evidence = out / 'evidence'
    evidence.mkdir()
    inspect_code = 'import json,sys;from pypdf import PdfReader;r=PdfReader(sys.argv[1]);print(json.dumps({"pages":len(r.pages),"text":"\\n".join(p.extract_text() or "" for p in r.pages)}))'

    def inspect(label, pdf, expected_pages, required):
        result = json.loads(command(label, [alpha, '-I', '-c', inspect_code, pdf]))
        assert result['pages'] == expected_pages
        assert all(text in result['text'] for text in required), result
        return {'pages': result['pages'], 'required_text': required, 'pdf_sha256': sha256(pdf.read_bytes()).hexdigest()}

    command('first-document', [alpha, 'first_document.py'], cwd=starter)
    first = inspect('first-document-read', starter / 'order.pdf', 1, ['Ready to ship', 'Studio notebook', '$360.00', 'Approved'])
    assert '<style' in (starter / 'order.html').read_text(encoding='utf-8')
    assert '<style' not in (starter / 'order.unstyled.html').read_text(encoding='utf-8')
    for name in ['order.pdf', 'order.html', 'order.unstyled.html']:
        shutil.copyfile(starter / name, evidence / ('first-' + name))
    source = (starter / 'first_document.py').read_text(encoding='utf-8')
    for before, after in [('Studio notebook', 'Field journal'), ('"quantity": 24', '"quantity": 36'), ('$360.00', '$540.00')]:
        assert source.count(before) == 1
        source = source.replace(before, after)
    (starter / 'edited_first_document.py').write_text(source, encoding='utf-8')
    command('edited-first-document', [alpha, 'edited_first_document.py'], cwd=starter)
    edited = inspect('edited-first-document-read', starter / 'order.pdf', 1, ['Field journal', '36', '$540.00'])
    assert edited['pdf_sha256'] != first['pdf_sha256']
    for name in ['order.pdf', 'order.html', 'order.unstyled.html']:
        shutil.copyfile(starter / name, evidence / ('edited-' + name))

    showcase = out / 'alpha/component-showcase'
    command('showcase-comparison', [alpha, 'examples/design_showcase/compare_authoring.py', '--out', 'output'], cwd=showcase)
    comparison = json.loads((showcase / 'output/comparison.json').read_text(encoding='utf-8'))
    assert comparison['ok'] and comparison['engine_version'] == '2.6.0a4'
    rendered = {}
    for lane in ['html', 'components']:
        for document, pages, text in [('invoice', 1, ['Northstar', 'Maple & Finch']), ('report', 3, ['Common Ground'])]:
            path = showcase / 'output' / lane / document / (document + '.pdf')
            rendered[lane + '/' + document] = inspect('showcase-' + lane + '-' + document, path, pages, text)
    result = {'ok': True, 'checked_at': datetime.now(timezone.utc).isoformat(), 'platform': sys.platform,
              'python': sys.version.split()[0], 'installer_versions': VERSIONS,
              'registry': registry or PUBLIC_REGISTRY, 'default_registry': args.default_registry,
              'installs': checks, 'integrity_rejection': True, 'existing_files_preserved': True,
              'first_document': first, 'edited_document': edited, 'showcase': rendered,
              'matching_showcase_pages': 4, 'styled_and_unstyled_html': True,
              'scope': 'Installs and renders the two pinned component kits; no general rendering or conformance claim.'}
    save(out / 'verification.json', result)
    print(json.dumps(result), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path(__file__).absolute().parents[1] / 'manifest.json')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--stable-python', type=Path)
    parser.add_argument('--alpha-python', type=Path)
    origin = parser.add_mutually_exclusive_group()
    origin.add_argument('--registry-url')
    origin.add_argument('--default-registry', action='store_true')
    args = parser.parse_args()
    try:
        verify(args)
    except Exception as error:
        if args.out.is_dir():
            save(args.out / 'failure.json', {'ok': False, 'error': str(error)})
        raise


if __name__ == '__main__':
    main()
