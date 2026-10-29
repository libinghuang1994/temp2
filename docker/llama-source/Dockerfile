FROM ghcr.io/libinghuang1994/qwen35-cpu-dev@sha256:e5a4a26394f87bf1c6c15fd2a4649828e15a5f2947cd9db8a34c82d755237dcd AS verification

ARG VCS_REF=unknown

LABEL org.opencontainers.image.title="Qwen3.5 CPU development environment with pinned llama.cpp source" \
      org.opencontainers.image.description="Verified 0.2.0 toolchain and Jupyter, plus an exportable unmodified llama.cpp v0.7.0 source archive; no model or compiled llama binaries" \
      org.opencontainers.image.source="https://github.com/libinghuang1994/temp2" \
      org.opencontainers.image.version="0.2.0-llama-src-v0.7.0" \
      org.opencontainers.image.revision="${VCS_REF}" \
      io.qwen35.llama.source-revision="620d2225cc436ab0b001e3200e590e3b286ef9ab"

COPY source.json /opt/llama-source/source.json
RUN mkdir -p /opt/llama-source \
    && curl --fail --silent --show-error --location --retry 3 --connect-timeout 30 --max-time 300 \
       https://codeload.github.com/ggml-org/llama.cpp/tar.gz/620d2225cc436ab0b001e3200e590e3b286ef9ab \
       --output /opt/llama-source/llama.cpp-v0.7.0.tar.gz \
    && printf '%s  %s\n' \
       1d4a987d9bd048f6e93107e838026438df70fbde237fc0c69c63d600512b4bd9 \
       llama.cpp-v0.7.0.tar.gz > /opt/llama-source/SHA256SUMS \
    && cd /opt/llama-source && sha256sum --check --strict SHA256SUMS \
    && tar -xOf llama.cpp-v0.7.0.tar.gz \
       llama.cpp-620d2225cc436ab0b001e3200e590e3b286ef9ab/LICENSE > LICENSE.llama.cpp

COPY export-llama-source.sh /usr/local/bin/export-llama-source
COPY verify-llama-source.sh /usr/local/bin/verify-llama-source
RUN chmod 0755 /usr/local/bin/export-llama-source /usr/local/bin/verify-llama-source

WORKDIR /workspace
CMD ["/bin/bash"]

# Data-only distribution: the development environment is used for verification
# above, but its layers are not included in the published source image.
FROM scratch AS source
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="Pinned llama.cpp v0.7.0 source archive" \
      org.opencontainers.image.description="Data-only source distribution; extract with docker create and docker cp" \
      org.opencontainers.image.source="https://github.com/libinghuang1994/temp2" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="llama-src-v0.7.0" \
      org.opencontainers.image.licenses="MIT" \
      io.qwen35.llama.source-revision="620d2225cc436ab0b001e3200e590e3b286ef9ab"
COPY --from=verification /opt/llama-source/ /opt/llama-source/
COPY export-llama-source.sh /opt/llama-source/export-llama-source.sh
