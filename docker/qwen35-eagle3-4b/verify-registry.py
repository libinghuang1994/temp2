#!/usr/bin/env python3
"""Verify a GHCR manifest and download every blob with anonymous pull auth."""
import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('reference', help='ghcr.io/OWNER/PACKAGE@sha256:DIGEST')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    path, digest = args.reference.removeprefix('ghcr.io/').split('@', 1)
    assert digest.startswith('sha256:') and len(digest) == 71
    args.output.mkdir(parents=True, exist_ok=True)
    query = urllib.parse.urlencode({'service': 'ghcr.io', 'scope': 'repository:' + path + ':pull'})
    with urllib.request.urlopen('https://ghcr.io/token?' + query, timeout=60) as response:
        token = json.load(response)['token']
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json'}
    def fetch(suffix):
        return urllib.request.urlopen(urllib.request.Request('https://ghcr.io/v2/' + path + suffix, headers=headers), timeout=120)
    with fetch('/manifests/' + digest) as response:
        manifest_raw = response.read()
    assert 'sha256:' + hashlib.sha256(manifest_raw).hexdigest() == digest
    manifest = json.loads(manifest_raw)
    if 'manifests' in manifest:
        (args.output / 'index.json').write_bytes(manifest_raw)
        choices = [m for m in manifest['manifests'] if m.get('platform', {}).get('os') == 'linux'
                   and m.get('platform', {}).get('architecture') == 'amd64']
        assert len(choices) == 1, 'Expected exactly one linux/amd64 image'
        digest = choices[0]['digest']
        with fetch('/manifests/' + digest) as response:
            manifest_raw = response.read()
        assert 'sha256:' + hashlib.sha256(manifest_raw).hexdigest() == digest
        manifest = json.loads(manifest_raw)
    assert 'config' in manifest and 'layers' in manifest, 'Expected a single-platform manifest'
    (args.output / 'manifest.json').write_bytes(manifest_raw)
    records = []
    for item in [manifest['config'], *manifest['layers']]:
        h = hashlib.sha256()
        size = 0
        with fetch('/blobs/' + item['digest']) as response:
            for block in iter(lambda: response.read(8 * 1024 * 1024), b''):
                h.update(block)
                size += len(block)
        assert 'sha256:' + h.hexdigest() == item['digest'] and size == item['size']
        records.append({'digest': item['digest'], 'bytes': size})
        print('PASS: anonymously downloaded and hashed', item['digest'], size, flush=True)
    result = {'reference': args.reference, 'platform_manifest_digest': digest,
              'manifest_digest_verified': True, 'anonymous_complete_pull': True,
              'compressed_blobs_bytes': sum(x['bytes'] for x in records), 'blobs': records}
    (args.output / 'anonymous-verification.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
