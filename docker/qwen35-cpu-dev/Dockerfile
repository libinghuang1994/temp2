FROM ubuntu:22.04@sha256:e0f80c829509ef4df9e76bd8944eb7b8ec25cbb379b112a7f9448b2c77a77c9b

ARG DEBIAN_FRONTEND=noninteractive
ARG CMAKE_VERSION=3.31.6
ARG CMAKE_SHA256=5a1133ff103c71eb5120e2cc3de922733e7d8a26a98ae716397e8676adb367bf
ARG IMAGE_VERSION=0.1.0
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.title="Qwen3.5 CPU development environment" \
      org.opencontainers.image.description="Ubuntu 22.04 amd64 with GCC 12, CMake 3.31.6, OpenMP, OpenSSL, libcurl and NUMA development tools" \
      org.opencontainers.image.source="https://github.com/libinghuang1994/temp2" \
      org.opencontainers.image.version="${IMAGE_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}"

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=Etc/UTC \
    CC=/usr/bin/gcc-12 \
    CXX=/usr/bin/g++-12 \
    PATH=/opt/cmake/bin:${PATH}

COPY apt-packages.txt /tmp/apt-packages.txt
RUN test "$(dpkg --print-architecture)" = amd64 \
    && apt-get update \
    && xargs -r apt-get install -y --no-install-recommends < /tmp/apt-packages.txt \
    && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 120 \
        --slave /usr/bin/g++ g++ /usr/bin/g++-12 \
        --slave /usr/bin/gcov gcov /usr/bin/gcov-12 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/apt-packages.txt

# Use the official Kitware binary and verify its published SHA-256.
RUN curl --fail --show-error --location --retry 3 --connect-timeout 30 --max-time 300 \
        "https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-linux-x86_64.tar.gz" \
        --output /tmp/cmake.tar.gz \
    && printf '%s  %s\n' "${CMAKE_SHA256}" /tmp/cmake.tar.gz | sha256sum --check --strict - \
    && mkdir -p /opt/cmake \
    && tar -xzf /tmp/cmake.tar.gz --directory /opt/cmake --strip-components=1 \
    && rm /tmp/cmake.tar.gz \
    && mkdir -p /usr/local/share/qwen35-cpu-dev \
    && printf 'image_version=%s\nbuild_date=%s\nsource_revision=%s\ncmake_version=%s\ncmake_archive_sha256=%s\n' \
        "${IMAGE_VERSION}" "${BUILD_DATE}" "${VCS_REF}" "${CMAKE_VERSION}" "${CMAKE_SHA256}" \
        > /usr/local/share/qwen35-cpu-dev/build-info.txt \
    && dpkg-query --show --showformat='${binary:Package}\t${Version}\n' \
        > /usr/local/share/qwen35-cpu-dev/packages.tsv

COPY verify-dev-env.sh /usr/local/bin/verify-dev-env
RUN chmod 0755 /usr/local/bin/verify-dev-env \
    && verify-dev-env > /usr/local/share/qwen35-cpu-dev/build-verification.log 2>&1 \
    && cat /usr/local/share/qwen35-cpu-dev/build-verification.log

WORKDIR /workspace
CMD ["/bin/bash"]
