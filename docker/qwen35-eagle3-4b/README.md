# Qwen3.5-4B 配对 EAGLE3 草稿头分发镜像

镜像：`ghcr.io/libinghuang1994/qwen35-cpu-dev:eagle3-qwen35-4b-v1`。

2026-11-06 [构建发布成功](https://github.com/libinghuang1994/temp2/actions/runs/42148844449)，已完成匿名下载全部镜像层并核对摘要。压缩镜像层及配置共 764,733,606 字节，约 765 MB；解包约 995 MB。云端 `docker save/load`、镜像内文件提取和覆盖保护均通过，详见[发布记录](release-v1.json)。

固定镜像摘要为 `sha256:50a4f18e786aec5c9ffedc07403585fe251ba74638b72b9142c8e902bfa4d3e4`。

沿用此前 `llama-src-v0.7.0` 的 GHCR 仓库，以 scratch 数据镜像分发；不需要替换现有开发容器。镜像内目录为 `/opt/qwen35-eagle3-4b`。原始 BF16 权重约 466 MB，F16 GGUF 为 477,099,552 字节，约 477 MB，另附主模型 tokenizer、固定转换器源码归档、转换修正、许可证、来源和校验记录。

## 下载和内网交付

在能访问 GHCR 的电脑执行：

```bash
docker pull --platform linux/amd64 ghcr.io/libinghuang1994/qwen35-cpu-dev:eagle3-qwen35-4b-v1
docker save --output qwen35-4b-eagle3-v1.tar ghcr.io/libinghuang1994/qwen35-cpu-dev:eagle3-qwen35-4b-v1
```

也可按固定摘要拉取，并给它加上分发标签后再执行上面的 `docker save`：

```bash
docker pull --platform linux/amd64 ghcr.io/libinghuang1994/qwen35-cpu-dev@sha256:50a4f18e786aec5c9ffedc07403585fe251ba74638b72b9142c8e902bfa4d3e4
docker tag ghcr.io/libinghuang1994/qwen35-cpu-dev@sha256:50a4f18e786aec5c9ffedc07403585fe251ba74638b72b9142c8e902bfa4d3e4 ghcr.io/libinghuang1994/qwen35-cpu-dev:eagle3-qwen35-4b-v1
```

云端导出 tar 约 995 MB；不同 Docker 版本、存储后端可能导出不同的 tar 字节和大小，以镜像摘要及提取后的 `SHA256SUMS` 为准。

将 tar 交给管理员；在有 Docker 的机器导入并提取：

```bash
docker load --input qwen35-4b-eagle3-v1.tar
(
    set -euo pipefail
    mkdir qwen35-eagle3-bundle
    head_container=$(docker create ghcr.io/libinghuang1994/qwen35-cpu-dev:eagle3-qwen35-4b-v1 /data-only)
    trap 'docker rm "$head_container" >/dev/null' EXIT
    docker cp "$head_container:/opt/qwen35-eagle3-4b/." ./qwen35-eagle3-bundle/
    cd qwen35-eagle3-bundle
    sha256sum --check --strict SHA256SUMS
)
```

`/data-only` 只用于创建停止状态的容器，不会执行。将提取目录放入现有开发容器可访问的位置，再执行（目标目录必须不存在）：

```bash
bash ./qwen35-eagle3-bundle/export-head.sh /mnt/huanglibing3/models/draft/Qwen3.5-4B-EAGLE3-v1
```

GGUF 路径为：

```text
/mnt/huanglibing3/models/draft/Qwen3.5-4B-EAGLE3-v1/gguf/Qwen3.5-4B-EAGLE3-F16.gguf
```

## 内容与适配

- 原始头：[yuyijiong/Qwen3.5-4B-Eagle3](https://huggingface.co/yuyijiong/Qwen3.5-4B-Eagle3/tree/f33c6e5e4fbfff68e8374a7eafebfd420fb37109)，固定提交 `f33c6e5e4fbfff68e8374a7eafebfd420fb37109`，Apache-2.0。原始权重 SHA-256 为 `3de3a9711bee96f571759a36d3becf22a45e012006401ae7ca47be796b0df29b`。
- 目标为 Qwen3.5-4B；单层、hidden 2560、16 Q / 4 KV 头、每头 160 维、缩减词表 50000。不是完整的 0.8B 独立草稿模型。
- 使用固定 llama.cpp 提交 `620d2225cc436ab0b001e3200e590e3b286ef9ab` 转换，未更换运行时版本。`converter/recipe/patch-converter.py` 仅修正这个 BF16 EAGLE3 转换路径的 partial RoPE：写入 40 维旋转元数据，且仅重排 Q/K 每头前 40 行，其余 120 行保留。没有修改 C++ 推理代码；此修正不是 NVFP4 转换支持声明。
- 训练器使用第 1/15/28 层输出；llama.cpp 使用层输入坐标，因此 GGUF 提取层为 2/16/29。保留这一坐标换算。
- 原始 `d2t` 是偏移值；GGUF 保存加上索引后的绝对 token ID，且逐项与原始 `t2d` mask 核对。
- F16 文件没有做低比特量化：矩阵为 F16、归一化权重为 F32，原始文件不改动。
- 此头借用目标模型的 token embedding，不能独立作为聊天模型启动。后续服务应使用 `draft-eagle3`；现有脚本的 `draft-simple` profile 不能直接装这个头。导入本镜像不会改动服务、AMX 构建、主模型或并发设置。

## 验证范围与记录

发布前检查全部源文件 SHA-256、14 个 GGUF tensor 的逐元素转换结果、词表映射、tokenizer 长度和关键元数据。以固定版 llama.cpp 的 CPU 后端加载全部权重并启用 tensor 检查；用真实 Q/K 权重生成输入，在位置 0、3、127 对比 GGML CPU 的 40 维 partial RoPE 与训练时的旋转约定。

`PROVENANCE.json` 和 `verification/` 保存实际校验结果。上述检查不等于配对 4B 的完整生成验收；尚未在目标服务器验证 EAGLE3 完整生成、Q8_0 主模型匹配、AMX 执行、24 并发接受率和吞吐，也不承诺达到 20 秒目标。

## 重建

在 Python 3.10–3.12、具备 CMake/C++ 编译器的联网 Linux 环境执行。使用新工作目录，避免与既有服务源码混用：

```bash
python3 -m venv /tmp/eagle3-build-venv
/tmp/eagle3-build-venv/bin/pip install -r docker/qwen35-eagle3-4b/requirements.txt
/tmp/eagle3-build-venv/bin/python docker/qwen35-eagle3-4b/prepare-bundle.py --work-dir /tmp/eagle3-package
docker build --platform linux/amd64 -f docker/qwen35-eagle3-4b/Dockerfile \
  -t ghcr.io/libinghuang1994/qwen35-cpu-dev:eagle3-qwen35-4b-v1 /tmp/eagle3-package
```

完整的 tokenizer 和原始转换器归档已附在数据镜像内；离线重新转换还需要预先准备 requirements 所列 Python 依赖。镜像不包含 PyTorch、开发环境、已编译二进制或 4B 主模型。
