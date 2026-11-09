FROM scratch
ARG VCS_REF=unknown
ARG PART_NUMBER
LABEL org.opencontainers.image.title="Qwen3.5-4B EAGLE3 v1 download part" \
      org.opencontainers.image.description="One of four 200 MiB chunks of the verified original data layer; collect all four and run reassemble.sh" \
      org.opencontainers.image.source="https://github.com/libinghuang1994/temp2" \
      org.opencontainers.image.version="eagle3-qwen35-4b-v1-200m" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.licenses="Apache-2.0 AND MIT" \
      io.qwen35.split.part="${PART_NUMBER}" \
      io.qwen35.split.total="4" \
      io.qwen35.original.manifest="sha256:50a4f18e786aec5c9ffedc07403585fe251ba74638b72b9142c8e902bfa4d3e4"
COPY payload/ /opt/qwen35-eagle3-split/
