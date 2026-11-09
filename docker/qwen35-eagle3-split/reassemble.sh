#!/usr/bin/env bash
# Run after copying /opt/qwen35-eagle3-split/. from all four part images.
set -euo pipefail
umask 077

if test "$#" -gt 1; then
    printf '用法：bash reassemble.sh [新的解包目录]\n' >&2
    exit 2
fi
destination=${1:-qwen35-eagle3-restored}
case "$destination" in
    /*) ;;
    *) destination="$PWD/$destination" ;;
esac
if test -e "$destination" || test -L "$destination"; then
    printf '解包目录已存在，请使用新目录：%s\n' "$destination" >&2
    exit 1
fi
cd -- "$(dirname -- "$0")"

parts=(layer.blob.part01 layer.blob.part02 layer.blob.part03 layer.blob.part04)
sha256sum --check --strict PARTS.SHA256SUMS
actual_sha=$(cat -- "${parts[@]}" | sha256sum | awk '{print $1}')
expected_sha=f5132305517a11cca973ef4afa7f5af85329710a439cb60c05a08d0290aff8be
if test "$actual_sha" != "$expected_sha"; then
    printf '合并层 SHA256 不符，已停止。\n' >&2
    exit 1
fi
printf 'ORIGINAL_LAYER_SHA256=PASS\n'
mkdir -- "$destination"
cat -- "${parts[@]}" | tar --extract --gzip --no-same-owner --directory "$destination"
bundle="$destination/opt/qwen35-eagle3-4b"
(
    cd -- "$bundle"
    sha256sum --check --strict SHA256SUMS
    printf '%s  %s\n' \
        1b76f2f3af3e9ce4fc7d240ff82b10ee9885fdd080390d1c3de0532ec292bf62 \
        gguf/Qwen3.5-4B-EAGLE3-F16.gguf | sha256sum --check --strict -
)
printf '\nRESULT=PASS\nBUNDLE_ROOT=%s\n' "$bundle"
printf '再执行：bash "%s/export-head.sh" /mnt/huanglibing3/models/draft/Qwen3.5-4B-EAGLE3-v1\n' "$bundle"
