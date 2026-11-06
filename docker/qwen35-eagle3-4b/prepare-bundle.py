#!/usr/bin/env python3
"""Download, convert, and verify the pinned data image payload."""
import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def run(argv, log=None, env=None):
    print('+', ' '.join(map(str, argv)), flush=True)
    if log:
        with log.open('w') as f:
            subprocess.run(list(map(str, argv)), check=True, stdout=f, stderr=subprocess.STDOUT, env=env)
    else:
        subprocess.run(list(map(str, argv)), check=True, env=env)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    recipe = Path(__file__).resolve().parent
    spec = json.loads((recipe / 'sources.json').read_text())
    work = args.work_dir.resolve()
    bundle = work / 'bundle'
    bundle.mkdir(parents=True, exist_ok=True)
    for item in spec['files']:
        path = bundle / item['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            partial = path.with_name(path.name + '.partial')
            run(['curl', '--fail', '--silent', '--show-error', '--location', '--retry', '3',
                 '--connect-timeout', '30', '--max-time', '900', item['url'], '--output', partial])
            partial.rename(path)
        if path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
            raise SystemExit('Source verification failed: ' + str(path))
        print('PASS: source SHA-256', item['path'], flush=True)

    source_parent = work / 'source'
    source_parent.mkdir(exist_ok=True)
    source = source_parent / ('llama.cpp-' + spec['llama_revision'])
    if not source.exists():
        run(['tar', '-xzf', bundle / 'converter/llama.cpp-v0.7.0.tar.gz', '-C', source_parent])
    converter = source / 'conversion/llama.py'
    if digest(converter) == spec['converter_original_sha256']:
        run([sys.executable, recipe / 'patch-converter.py', source])
    if digest(converter) != spec['converter_patched_sha256']:
        raise SystemExit('Patched converter checksum mismatch')
    shutil.copy2(source / 'LICENSE', bundle / 'converter/LICENSE.llama.cpp')

    records = bundle / 'verification'
    records.mkdir(exist_ok=True)
    gguf = bundle / 'gguf/Qwen3.5-4B-EAGLE3-F16.gguf'
    gguf.parent.mkdir(exist_ok=True)
    if not gguf.exists():
        env = dict(os.environ, HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', OMP_NUM_THREADS='2')
        run([sys.executable, source / 'convert_hf_to_gguf.py', bundle / 'original',
             '--target-model-dir', bundle / 'target-tokenizer', '--outtype', 'f16', '--outfile', gguf],
            records / 'conversion.log', env)
    if digest(gguf) != spec['gguf_sha256'] or gguf.stat().st_size != spec['gguf_bytes']:
        raise SystemExit('Converted GGUF checksum mismatch')
    run([sys.executable, recipe / 'verify-gguf.py', bundle, source], records / 'gguf-verification.log')

    build = work / 'build'
    run(['cmake', '-S', source, '-B', build, '-DCMAKE_BUILD_TYPE=Release',
         '-DGGML_NATIVE=OFF', '-DGGML_BACKEND_DL=OFF', '-DGGML_CPU_ALL_VARIANTS=OFF',
         '-DGGML_CUDA=OFF', '-DGGML_VULKAN=OFF', '-DGGML_BLAS=OFF', '-DLLAMA_CURL=OFF',
         '-DLLAMA_BUILD_TESTS=OFF', '-DLLAMA_BUILD_EXAMPLES=OFF', '-DLLAMA_BUILD_TOOLS=OFF',
         '-DLLAMA_BUILD_UI=OFF', '-DLLAMA_USE_PREBUILT_UI=OFF',
         '-DLLAMA_BUILD_COMMIT=' + spec['llama_revision']], records / 'cmake.log')
    run(['cmake', '--build', build, '--target', 'llama', '--parallel', args.jobs], records / 'build.log')
    verifier = work / 'verify-cpu'
    run(['c++', '-std=c++17', '-O2', '-I' + str(source / 'include'), '-I' + str(source / 'ggml/include'),
         recipe / 'verify-cpu.cpp', '-L' + str(build / 'bin'), '-Wl,-rpath,' + str(build / 'bin'),
         '-lllama', '-lggml', '-lggml-base', '-lggml-cpu', '-o', verifier], records / 'verifier-build.log')
    fixtures = sorted(records.glob('rope-*.bin'))
    run([verifier, gguf, *fixtures], records / 'cpu-verification.log')

    converter_recipe = bundle / 'converter/recipe'
    converter_recipe.mkdir(exist_ok=True)
    for name in ['sources.json', 'patch-converter.py', 'prepare-bundle.py', 'verify-gguf.py',
                 'verify-cpu.cpp', 'requirements.txt', 'Dockerfile', '.dockerignore', 'export-head.sh', 'README.md']:
        shutil.copy2(recipe / name, converter_recipe / name)
    shutil.copy2(recipe / '.dockerignore', work / '.dockerignore')
    shutil.copy2(recipe / 'export-head.sh', bundle / 'export-head.sh')
    shutil.copy2(recipe / 'README.md', bundle / 'README.md')
    provenance = dict(spec)
    provenance.update({
        'conversion': 'BF16 original -> F16 matrices / F32 norms; partial Q/K RoPE row permutation',
        'feature_layer_coordinate_translation': {'trainer_output_layers': [1, 15, 28], 'llama_input_layers': [2, 16, 29]},
        'python_version': sys.version.split()[0],
        'python_packages': {p: importlib.metadata.version(p) for p in ['torch', 'numpy', 'transformers', 'safetensors']},
        'checks': {'upstream_checksums': 'passed', 'all_gguf_tensors_and_metadata': 'passed',
                   'fixed_llama_cpu_weight_load_and_tensor_check': 'passed', 'ggml_cpu_partial_rope_real_weight_fixtures': 'passed',
                   'paired_4b_end_to_end_generation': 'not_performed', 'target_amx_execution': 'not_performed',
                   'target_24_concurrent_acceptance_and_throughput': 'not_performed'},
    })
    (bundle / 'PROVENANCE.json').write_text(json.dumps(provenance, indent=2) + '\n')
    paths = sorted(p for p in bundle.rglob('*') if p.is_file() and p.name != 'SHA256SUMS')
    (bundle / 'SHA256SUMS').write_text(''.join(digest(p) + '  ' + p.relative_to(bundle).as_posix() + '\n' for p in paths))
    print('PASS: complete verified bundle:', bundle, flush=True)


if __name__ == '__main__':
    main()
