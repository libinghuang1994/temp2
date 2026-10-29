#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || "$1" != /* ]]; then
    printf '%s\n' 'Usage: export-llama-source /absolute/path/to/new/llama.cpp-v0.7.0' >&2
    exit 2
fi

destination=${1%/}
if [[ -z "$destination" || -e "$destination" || -L "$destination" ]]; then
    printf 'Destination must not exist: %s\n' "$1" >&2
    exit 2
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ -f "$script_dir/SHA256SUMS" ]]; then
    bundle=$script_dir
else
    bundle=/opt/llama-source
fi
(cd "$bundle" && sha256sum --check --strict SHA256SUMS)

parent=$(dirname -- "$destination")
mkdir -p -- "$parent"
staging=$(mktemp -d "$parent/.llama-source.XXXXXX")
trap 'if [[ -n "$staging" && -d "$staging" ]]; then rm -rf -- "$staging"; fi' EXIT

tar -xzf "$bundle/llama.cpp-v0.7.0.tar.gz" --directory "$staging" \
    --strip-components=1 --no-same-owner
test -s "$staging/LICENSE"
test -f "$staging/CMakeLists.txt"
test -f "$staging/include/llama.h"
cp -- "$bundle/source.json" "$staging/SOURCE_PROVENANCE.json"
mv --no-clobber --no-target-directory -- "$staging" "$destination"
if [[ -d "$staging" ]]; then
    printf 'Destination appeared during export; nothing overwritten: %s\n' "$destination" >&2
    exit 2
fi
staging=

printf 'PASS: llama.cpp v0.7.0 source exported to %s\n' "$destination"
printf '%s\n' 'Upstream commit: 620d2225cc436ab0b001e3200e590e3b286ef9ab'
