#!/usr/bin/env python3
"""Split the pinned original compressed data layer into four small image contexts."""
import argparse
import hashlib
import json
import shutil
import urllib.parse
import urllib.request
from pathlib import Path

REPOSITORY = 'libinghuang1994/qwen35-cpu-dev'
MANIFEST = '50a4f18e786aec5c9ffedc07403585fe251ba74638b72b9142c8e902bfa4d3e4'
LAYER_SHA = 'f5132305517a11cca973ef4afa7f5af85329710a439cb60c05a08d0290aff8be'
LAYER_BYTES = 764731594
CHUNK_BYTES = 200 * 1024 * 1024
EXPECTED_PARTS = 4
RECIPE = Path(__file__).resolve().parent


def hash_file(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


class RegistryRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None and urllib.parse.urlparse(req.full_url).netloc != urllib.parse.urlparse(newurl).netloc:
            redirected.remove_header('Authorization')
        return redirected


def download_layer(output):
    query = urllib.parse.urlencode({'service': 'ghcr.io', 'scope': f'repository:{REPOSITORY}:pull'})
    opener = urllib.request.build_opener(RegistryRedirect())
    with opener.open('https://ghcr.io/token?' + query, timeout=60) as response:
        token = json.load(response)['token']
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json'}
    url = f'https://ghcr.io/v2/{REPOSITORY}/manifests/sha256:{MANIFEST}'
    with opener.open(urllib.request.Request(url, headers=headers), timeout=120) as response:
        raw = response.read()
    if hashlib.sha256(raw).hexdigest() != MANIFEST:
        raise ValueError('Original manifest digest mismatch')
    manifest = json.loads(raw)
    layers = manifest['layers']
    if len(layers) != 1 or layers[0]['digest'] != 'sha256:' + LAYER_SHA or layers[0]['size'] != LAYER_BYTES:
        raise ValueError('Unexpected original layer descriptor')
    url = f'https://ghcr.io/v2/{REPOSITORY}/blobs/sha256:{LAYER_SHA}'
    with opener.open(urllib.request.Request(url, headers=headers), timeout=180) as response, output.open('xb') as stream:
        shutil.copyfileobj(response, stream, 8 * 1024 * 1024)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, required=True, help='New directory; existing paths are refused')
    parser.add_argument('--layer', type=Path, help='Optional existing complete original compressed layer')
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=False)
    layer = args.layer or download_layer(args.work_dir / 'original.layer.blob')
    if layer.stat().st_size != LAYER_BYTES or hash_file(layer) != LAYER_SHA:
        raise SystemExit('Original compressed layer size or SHA256 mismatch; no image contexts produced')
    records = []
    with layer.open('rb') as stream:
        for number in range(1, EXPECTED_PARTS + 1):
            payload = args.work_dir / f'part{number:02d}' / 'payload'
            payload.mkdir(parents=True)
            name = f'layer.blob.part{number:02d}'
            block = stream.read(CHUNK_BYTES)
            if not block:
                raise ValueError('Missing part')
            (payload / name).write_bytes(block)
            records.append({'number': number, 'filename': name, 'bytes': len(block),
                            'sha256': hashlib.sha256(block).hexdigest(),
                            'tag': f'eagle3-qwen35-4b-v1-200m-part{number:02d}'})
        if stream.read(1):
            raise ValueError('More than four parts')
    result = {'schema_version': 1, 'source_image': f'ghcr.io/{REPOSITORY}@sha256:{MANIFEST}',
              'source_layer_sha256': LAYER_SHA, 'source_layer_bytes': LAYER_BYTES,
              'chunk_bytes': CHUNK_BYTES, 'part_count': EXPECTED_PARTS, 'parts': records,
              'gguf_sha256': '1b76f2f3af3e9ce4fc7d240ff82b10ee9885fdd080390d1c3de0532ec292bf62',
              'restores': 'Original data files, not a runnable application or Docker image archive'}
    metadata = json.dumps(result, indent=2) + '\n'
    sums = ''.join(f"{r['sha256']}  {r['filename']}\n" for r in records)
    (args.work_dir / 'split-record.json').write_text(metadata)
    for number in range(1, EXPECTED_PARTS + 1):
        payload = args.work_dir / f'part{number:02d}' / 'payload'
        (payload / 'SOURCE.json').write_text(metadata)
        (payload / 'PARTS.SHA256SUMS').write_text(sums)
        shutil.copy2(RECIPE / 'reassemble.sh', payload / 'reassemble.sh')
    print(metadata)


if __name__ == '__main__':
    main()
