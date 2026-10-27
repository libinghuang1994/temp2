#!/usr/bin/env bash
set -euo pipefail

for command_name in gcc g++ make ninja cmake git pkg-config python3 curl \
    sha256sum numactl ccache gdb rg file; do
    command -v "$command_name" > /dev/null
done

test "$(dpkg --print-architecture)" = amd64
test "$(gcc -dumpversion)" = 12
test "$(g++ -dumpversion)" = 12
cmake --version | sed -n '1p' | rg --quiet '^cmake version 3\.31\.6$'

gcc --version | sed -n '1p'
g++ --version | sed -n '1p'
cmake --version | sed -n '1p'
git --version
python3 --version
printf 'Ninja: '
ninja --version
printf 'glibc: '
getconf GNU_LIBC_VERSION
pkg-config --modversion openssl libcurl numa

verification_dir=$(mktemp -d)
trap 'rm -rf -- "$verification_dir"' EXIT

cat > "$verification_dir/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.14)
project(dev_env_verification LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(OpenMP REQUIRED)
find_package(OpenSSL REQUIRED)
find_package(CURL REQUIRED)
add_executable(verify main.cpp)
target_link_libraries(verify PRIVATE OpenMP::OpenMP_CXX OpenSSL::Crypto CURL::libcurl)
CMAKE

cat > "$verification_dir/main.cpp" <<'CPP'
#include <curl/curl.h>
#include <openssl/crypto.h>
#include <iostream>
#include <numeric>
#include <vector>
#ifndef _OPENMP
#error OpenMP must be enabled
#endif
int main() {
    std::vector<int> values(64);
    std::iota(values.begin(), values.end(), 0);
    int sum = 0;
    #pragma omp parallel for reduction(+:sum)
    for (int i = 0; i < 64; ++i) sum += values[i];
    if (sum != 2016 || curl_version_info(CURLVERSION_NOW) == nullptr) return 1;
    std::cout << "C++17 / OpenMP / libcurl passed; " << OpenSSL_version(OPENSSL_VERSION) << '\n';
}
CPP

cmake -S "$verification_dir" -B "$verification_dir/build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release
cmake --build "$verification_dir/build" --parallel 2
OMP_NUM_THREADS=2 "$verification_dir/build/verify"

cat > "$verification_dir/avx512.cpp" <<'CPP'
#include <immintrin.h>
__m512i verify_vnni(__m512i a, __m512i b, __m512i c) {
    return _mm512_dpbusd_epi32(a, b, c);
}
CPP
g++ -std=c++17 -O2 -mavx512f -mavx512bw -mavx512dq -mavx512vl -mavx512vnni \
    -c "$verification_dir/avx512.cpp" -o "$verification_dir/avx512.o"

cat > "$verification_dir/amx.cpp" <<'CPP'
#include <immintrin.h>
void verify_amx() {
    _tile_zero(0);
    _tile_dpbssd(0, 1, 2);
    _tile_dpbf16ps(0, 1, 2);
    _tile_release();
}
CPP
g++ -std=c++17 -O2 -mamx-tile -mamx-int8 -mamx-bf16 \
    -c "$verification_dir/amx.cpp" -o "$verification_dir/amx.o"

printf '%s\n' 'PASS: C/C++ build and runtime checks; AVX-512/VNNI and AMX compilation.'
printf '%s\n' 'ISA-specific objects were compiled only. Actual AMX execution must be verified on the target server.'
