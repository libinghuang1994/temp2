# llama.cpp v0.7.0 源码分发镜像

用于通过已有 GHCR 通道把固定版本源码送入内网，再导出到独立工作目录中修改和编译。

| 内容 | 固定值 |
|---|---|
| 分发标签 | `ghcr.io/libinghuang1994/qwen35-cpu-dev:0.2.0-llama-src-v0.7.0` |
| 开发环境 | 原 `0.2.0` 的固定摘要，保留工具链与 Jupyter |
| 上游版本 | `ggml-org/llama.cpp` 的 `v0.7.0` |
| 完整源码提交 | `620d2225cc436ab0b001e3200e590e3b286ef9ab` |
| 原始源码归档大小 | 38,195,486 字节，约 38.2 MB |
| 原始源码归档 SHA-256 | `1d4a987d9bd048f6e93107e838026438df70fbde237fc0c69c63d600512b4bd9` |

镜像继承原 `0.2.0` 的层，仅增加源码归档、来源记录和导出/验证脚本。源码原始归档与许可证保留，归档不含 `.git` 历史。导出时增加 `SOURCE_PROVENANCE.json` 记录来源。镜像不包含模型或编译后的 llama.cpp 程序。

默认命令仍为 `/bin/bash`，没有固定 ENTRYPOINT，继承 Jupyter 依赖和端口声明。平台可沿用原 `0.2.0` 的启动命令、认证与代理配置。

## 通过平台界面导入

1. 使用上表的分发标签，在平台创建一个源码开发容器；挂载用户确认的持久化工作目录。
2. 在新容器中，把源码导出到该持久化目录的新子目录。下面的路径需替换为实际挂载路径：

```bash
export-llama-source /持久化项目目录/src/llama.cpp-v0.7.0
```

导出目标必须不存在，脚本会校验归档并拒绝覆盖现有目录。解包后约占 181 MiB，实际磁盘分配随文件系统变化。

导出完成后，源码可由任何挂载了同一目录的原版 `0.2.0` 开发容器使用。后续修改和双配置编译都使用这份独立源码，不需要重新制作镜像。也可继续在新容器中开发。

## 有 Docker 终端时导出到本地目录

此方法要求当前终端能够访问 Docker 服务。`docker cp` 的目标目录属于运行命令的当前终端，因此适用于把源码从镜像复制到现有工作环境。

```bash
docker pull --platform linux/amd64 ghcr.io/libinghuang1994/qwen35-cpu-dev:0.2.0-llama-src-v0.7.0
```

在确认的项目目录中执行以下命令，归档会写入新建的 `llama-source-bundle` 子目录：

```bash
(
    set -euo pipefail
    mkdir llama-source-bundle
    source_container=$(docker create ghcr.io/libinghuang1994/qwen35-cpu-dev:0.2.0-llama-src-v0.7.0)
    trap 'docker rm "$source_container" >/dev/null' EXIT
    docker cp "$source_container:/opt/llama-source/." ./llama-source-bundle/
    cd llama-source-bundle
    sha256sum --check --strict SHA256SUMS
    mkdir llama.cpp-v0.7.0
    tar -xzf llama.cpp-v0.7.0.tar.gz --directory llama.cpp-v0.7.0 \
        --strip-components=1 --no-same-owner
    cp source.json llama.cpp-v0.7.0/SOURCE_PROVENANCE.json
)
```

这里使用 `docker create` 和 `docker cp`，不启动测试服务。保留已复制的源码归档和校验记录即可。

## 离线编译验证范围

发布流程使用 `--network none` 执行 `verify-llama-source`，导出并编译 `llama-cli`、`llama-server` 和 `llama-bench`，检查三者 `--help` 能运行；另行执行 Jupyter 验证。外部通用 CPU 编译验证不启用 AVX-512/AMX 专用路径。

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
