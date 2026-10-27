# Qwen3.5 CPU 开发镜像

这是用于修改、编译及首轮运行 llama.cpp 的 Ubuntu 22.04 amd64 开发环境。
源码、模型、构建目录和日志分别挂载。镜像不包含模型、llama.cpp 源码、PyTorch 或 CUDA。

## 工具链

- Ubuntu 22.04 官方基础镜像，Dockerfile 固定其摘要。
- GCC/G++ 12；`gcc`、`g++` 默认指向 12，`CC`、`CXX` 同时指定 12。
- CMake 3.31.6，使用 Kitware 官方二进制并校验固定 SHA-256。
- Make、Ninja、Git、pkg-config、Python 3、curl、CA 证书。
- OpenMP、OpenSSL、libcurl、NUMA 开发库及 numactl、ccache、GDB、ripgrep。

系统包安装列表见 [apt-packages.txt](apt-packages.txt)。系统包从 Ubuntu 源解析，
每次构建的实际版本保存在镜像内 `/usr/local/share/qwen35-cpu-dev/packages.tsv`。
固定基础镜像和 CMake 不代表 apt 依赖的所有版本均被冻结；使用最终镜像摘要可以取得同一构建产物。

## 内网使用

已发布地址：`ghcr.io/libinghuang1994/qwen35-cpu-dev:0.1.0`。
2026-10-27 已使用空 Docker 认证配置，从 GHCR 成功拉取最终摘要镜像，当前无需登录。
压缩层及配置共 300,746,659 字节，约 301 MB；云端构建记录的未压缩大小为
822,786,763 字节，约 823 MB。Docker 使用不同存储后端时，实际占用和显示值可能不同。
详细交付记录见 [release-0.1.0.json](release-0.1.0.json)。

```bash
docker pull --platform linux/amd64 ghcr.io/libinghuang1994/qwen35-cpu-dev:0.1.0
docker run --rm --network none ghcr.io/libinghuang1994/qwen35-cpu-dev:0.1.0 verify-dev-env
```

固定到本次构建产物可使用完整摘要：

```bash
docker pull --platform linux/amd64 ghcr.io/libinghuang1994/qwen35-cpu-dev@sha256:2ef869c7ad4e4113e55d3cfaf9500de4a1d7b0c2553924b342e5623496108f4d
```

构建和发布均已通过：[GitHub Actions 运行记录](https://github.com/libinghuang1994/temp2/actions/runs/40472090532)。

以下为开发容器示例，先将路径换成 Docker 服务端实际可访问的绝对目录：

```bash
docker run --rm -it \
  --mount type=bind,src=/绝对路径/llama.cpp,dst=/workspace/llama.cpp \
  --mount type=bind,src=/绝对路径/builds,dst=/builds \
  --mount type=bind,src=/绝对路径/models,dst=/models,readonly \
  --mount type=bind,src=/绝对路径/logs,dst=/logs \
  ghcr.io/libinghuang1994/qwen35-cpu-dev:0.1.0
```

挂载前创建对应目录。CPU、内存、NUMA 限制和端口应按实际 Docker 服务设置，
新容器不自动继承当前终端容器的配额。编译输出可放在 `/builds/avx512`、`/builds/amx`，
同一镜像可承担两套配置；具体 llama.cpp 构建参数需要对照选定提交。

## 验证范围

构建过程会调用 `verify-dev-env`，检查工具存在、版本正确，
通过 CMake/Ninja 编译并运行使用 C++17、OpenMP、OpenSSL、libcurl 的小程序，
并分别编译包含 AVX-512/VNNI 和 AMX-TILE/INT8/BF16 intrinsic 的对象文件。
AVX-512、AMX 测试对象仅编译，不执行，构建机器无需具备对应硬件。

这不代表 llama.cpp 已编译、模型已加载，也不代表 AMX 已在目标服务器实际执行。
目标侧仍需完成双配置编译、AMX 运行权限和计算验证、模型及 API 验收。

## 构建与发布

在仓库根目录可执行本地构建：

```bash
docker build --platform linux/amd64 \
  --tag ghcr.io/libinghuang1994/qwen35-cpu-dev:0.1.0 \
  docker/qwen35-cpu-dev
```

GitHub Actions 的 `Build Qwen35 CPU development image` 工作流可手动触发，
也会在 `main` 分支的 Dockerfile、依赖清单、验证脚本、构建上下文规则或工作流自身发生变化时触发。
推送触发默认发布 `0.1.0`，手动触发可指定版本；后续正式更新时应同时调整默认版本。
它在 `ubuntu-22.04` runner 构建 amd64 镜像，通过独立的离线容器验证后，
使用工作流临时令牌的 `packages: write` 权限发布至当前仓库所属账号的 GHCR。
工作流上传包版本清单、镜像信息和发布日志作为构建记录。

当前流程不自动改变包的可见性，不添加定时任务，也不包含服务器部署操作。

## 官方来源

- Ubuntu：<https://hub.docker.com/_/ubuntu>
- CMake 3.31.6：<https://github.com/Kitware/CMake/releases/tag/v3.31.6>
- CMake 校验清单：<https://github.com/Kitware/CMake/releases/download/v3.31.6/cmake-3.31.6-SHA-256.txt>
- GHCR：<https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry>
