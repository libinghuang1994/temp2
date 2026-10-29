# llama.cpp v0.7.0 源码分发镜像

用于通过已有 GHCR 通道把固定版本源码送入内网，再导出到独立工作目录中修改和编译。

| 内容 | 固定值 |
|---|---|
| 分发标签 | `ghcr.io/libinghuang1994/qwen35-cpu-dev:llama-src-v0.7.0` |
| 镜像内容 | 基于 scratch，仅包含源码归档、来源记录、许可证和导出脚本 |
| 编译验证环境 | 原 `0.2.0` 的固定摘要，工具链与 Jupyter 不进入最终源码镜像 |
| 上游版本 | `ggml-org/llama.cpp` 的 `v0.7.0` |
| 完整源码提交 | `620d2225cc436ab0b001e3200e590e3b286ef9ab` |
| 原始源码归档大小 | 38,195,486 字节，约 38.2 MB |
| 原始源码归档 SHA-256 | `1d4a987d9bd048f6e93107e838026438df70fbde237fc0c69c63d600512b4bd9` |

源码原始归档与许可证保留，归档不含 `.git` 历史。导出时增加 `SOURCE_PROVENANCE.json` 记录来源。最终镜像不包含开发环境、模型或编译后的 llama.cpp 程序。

这是用于 `docker create` / `docker cp` 的数据镜像，不作为开发容器启动。原版 `0.2.0` 开发镜像及已经启动的容器继续使用。

## 本地拉取，交由管理员导入

在能拉取 GHCR 镜像的本地终端执行：

```bash
docker pull --platform linux/amd64 ghcr.io/libinghuang1994/qwen35-cpu-dev:llama-src-v0.7.0
docker save --output llama-src-v0.7.0.tar ghcr.io/libinghuang1994/qwen35-cpu-dev:llama-src-v0.7.0
```

将 `llama-src-v0.7.0.tar` 交给管理员，管理员导入：

```bash
docker load --input llama-src-v0.7.0.tar
```

随后按下一节提取源码包，再将包目录交付到现有开发容器的持久化项目目录。

## 从源码镜像提取文件

在可访问 Docker 服务的 Bash 终端执行，可在本地完成，也可由管理员在服务器完成。归档会写入新建的 `llama-source-bundle` 子目录：

```bash
(
    set -euo pipefail
    mkdir llama-source-bundle
    source_container=$(docker create ghcr.io/libinghuang1994/qwen35-cpu-dev:llama-src-v0.7.0 /source-data-only)
    trap 'docker rm "$source_container" >/dev/null' EXIT
    docker cp "$source_container:/opt/llama-source/." ./llama-source-bundle/
    cd llama-source-bundle
    sha256sum --check --strict SHA256SUMS
)
```

`/source-data-only` 仅用于创建停止状态的容器，命令不会执行。这个镜像没有可运行的 shell，也无需启动进程。

## 在现有开发容器中解包

将 `llama-source-bundle` 放在已确认的持久化目录中，进入该目录后执行：

```bash
bash ./export-llama-source.sh "$PWD/llama.cpp-v0.7.0"
```

导出目标必须不存在，脚本会校验归档并拒绝覆盖现有目录。原始归档解包后约占 181 MiB，实际磁盘分配随文件系统变化。后续修改和双配置编译使用这份独立源码，不需要重新制作镜像。

## 离线编译验证范围

发布流程先从最终数据镜像提取源码包，再挂载到独立的开发验证镜像中，使用 `--network none` 执行 `verify-llama-source`，导出并编译 `llama-cli`、`llama-server` 和 `llama-bench`，检查三者 `--help` 能运行；另行检查复制出来的导出脚本及覆盖保护。外部 CPU 编译验证不启用 AVX-512/AMX 专用路径。

为避免内网编译时自动下载网页资源，此次离线验证使用该版本实际支持的参数：

```text
-DLLAMA_BUILD_UI=OFF
-DLLAMA_USE_PREBUILT_UI=OFF
-DLLAMA_BUILD_COMMIT=620d2225cc436ab0b001e3200e590e3b286ef9ab
```

前两项使服务器构建不包含内嵌聊天网页，HTTP API 仍可构建。需要内嵌网页时应另行准备匹配的 UI 产物。第三项使无 `.git` 的源码归档构建仍记录原始提交号。

这次源码交付不代表目标侧双配置构建、AMX 实际执行、模型推理或 HTTP API 已通过。最终发布证据以本目录的发布记录为准。

## 官方来源

- [上游 v0.7.0 发布页](https://github.com/ggml-org/llama.cpp/releases/tag/v0.7.0)
- [固定提交的源码](https://github.com/ggml-org/llama.cpp/tree/620d2225cc436ab0b001e3200e590e3b286ef9ab)
- [上游许可证](https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/LICENSE)
