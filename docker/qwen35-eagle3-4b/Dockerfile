FROM scratch
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="Qwen3.5-4B paired EAGLE3 draft head" \
      org.opencontainers.image.description="Data image: pinned original weights, partial-RoPE-corrected F16 GGUF, tokenizer, converter recipe, and verification records" \
      org.opencontainers.image.source="https://github.com/libinghuang1994/temp2" \
      org.opencontainers.image.version="eagle3-qwen35-4b-v1" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.licenses="Apache-2.0 AND MIT" \
      io.qwen35.eagle3.revision="f33c6e5e4fbfff68e8374a7eafebfd420fb37109" \
      io.qwen35.llama.revision="620d2225cc436ab0b001e3200e590e3b286ef9ab"
COPY bundle/ /opt/qwen35-eagle3-4b/
