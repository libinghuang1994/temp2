#!/usr/bin/env bash
set -euo pipefail
bundle_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ $# != 1 ]]; then
    printf 'Usage: bash export-head.sh NEW_DESTINATION\n' >&2
    exit 2
fi
destination=$(realpath -m -- "$1")
case "$destination/" in
    "$bundle_dir/"*) printf 'Destination must be outside the source bundle\n' >&2; exit 1 ;;
esac
if [[ -e "$destination" || -L "$destination" ]]; then
    printf 'Refusing to overwrite existing destination: %s\n' "$destination" >&2
    exit 1
fi
cd -- "$bundle_dir"
sha256sum --check --strict SHA256SUMS
mkdir -p -- "$(dirname -- "$destination")"
mkdir -- "$destination"
cp -a -- "$bundle_dir/." "$destination/"
printf 'Exported paired EAGLE3 bundle to: %s\n' "$destination"
