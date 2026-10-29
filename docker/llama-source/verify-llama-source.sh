#!/usr/bin/env bash
set -euo pipefail

verification_dir=$(mktemp -d)
trap 'rm -rf -- "$verification_dir"' EXIT
export-llama-source "$verification_dir/source"

# Keep this check portable to the external build runner. Target-specific
# AVX-512 and AMX builds and execution remain separate target-server checks.
cmake -S "$verification_dir/source" -B "$verification_dir/build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DLLAMA_BUILD_COMMIT=620d2225cc436ab0b001e3200e590e3b286ef9ab \
    -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_APP=OFF \
    -DLLAMA_BUILD_UI=OFF -DLLAMA_USE_PREBUILT_UI=OFF \
    -DGGML_NATIVE=OFF -DGGML_AVX=OFF -DGGML_AVX2=OFF \
    -DGGML_F16C=OFF -DGGML_FMA=OFF -DGGML_AVX512=OFF \
    -DGGML_AMX_TILE=OFF -DGGML_AMX_INT8=OFF -DGGML_AMX_BF16=OFF \
    -DGGML_CUDA=OFF -DGGML_VULKAN=OFF
cmake --build "$verification_dir/build" --parallel 2 \
    --target llama-cli llama-server llama-bench

for tool in llama-cli llama-server llama-bench; do
    "$verification_dir/build/bin/$tool" --help > "$verification_dir/$tool-help.txt" 2>&1
    test -s "$verification_dir/$tool-help.txt"
done
printf '%s\n' 'PASS: pinned source exported; offline CPU build and help checks for llama-cli, llama-server and llama-bench'
printf '%s\n' 'No model loaded. Target AVX-512/AMX execution and model/API validation remain pending.'
