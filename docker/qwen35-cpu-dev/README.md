# Qwen3.5 CPU 开发镜像

这是用于修改、编译及首轮运行 llama.cpp 的 Ubuntu 22.04 amd64 开发环境。
源码、模型、构建目录和日志分别挂载。镜像不包含模型、llama.cpp 源码、PyTorch 或 CUDA。

## 工具链

- Ubuntu 22.04 官方基础镜像，Dockerfile 固定其摘要。
- GCC/G++ 12；`gcc`、`g++` 默认指向 12，`CC`、`CXX` 同时指定 12。
- CMake 3.31.6，使用 Kitware 官方二进制并校验固定 SHA-256。
- Make、Ninja、Git、pkg-config、Python 3、curl、CA 证书。
- OpenMP、OpenSSL、libcurl、NUMA 开发库及 numactl、ccache、GDB、ripgrep。

## 0.2.0：内网平台所需的 Jupyter 依赖

`0.2.0` 通过 [Dockerfile.jupyter](Dockerfile.jupyter) 继承已发布 `0.1.0` 的固定摘要，
保留原 CPU 工具链，增加以下 Python 包和所需的全部传递依赖：

| 包 | 固定版本 |
|---|---|
| IPython | 8.12.2（管理员指定） |
| Notebook | 6.5.2（管理员指定） |
| JupyterLab | 4.5.11 |
| 简体中文语言包 `jupyterlab-language-pack-zh-CN` | 4.5.post3 |
| traitlets | 5.9.0 |

管理员命令里的 `jupyterlab-language-ppack-zh-CN` 多了一个 `p`，已按
[Jupyter 官方说明](https://jupyterlab.readthedocs.io/en/stable/user/language.html)修正。
固定 traitlets 5.9.0 是为了兼容 Notebook 6.5.2；上游问题见
[jupyter/notebook#7048](https://github.com/jupyter/notebook/issues/7048)。
JupyterLab 与中文包选择同一 4.5 系列；在 Settings → Language 中选择简体中文。

直接依赖见 [requirements-jupyter.in](requirements-jupyter.in)，100 个解析后的包及其 wheel
SHA-256 见 [requirements-jupyter.txt](requirements-jupyter.txt)。安装时启用 `--require-hashes`。
pip 固定为 25.3；包安装到镜像默认 Python 3.10 环境，`pip`、`python3 -m pip` 与
Python 内核使用该环境，无需在内网再执行 pip 安装。
镜像内实际 Python 包清单在 `/usr/local/share/qwen35-cpu-dev/python-packages.txt`。

拉取及断网验证命令：

```bash
docker pull --platform linux/amd64 ghcr.io/libinghuang1994/qwen35-cpu-dev:0.2.0
docker run --rm --network none ghcr.io/libinghuang1994/qwen35-cpu-dev:0.2.0 verify-dev-env
docker run --rm --network none ghcr.io/libinghuang1994/qwen35-cpu-dev:0.2.0 verify-jupyter-env
```

`verify-jupyter-env` 检查依赖版本和中文翻译文件，实际执行一个 Python Notebook 单元，
分别启动 JupyterLab 与 Notebook，验证带 token 的 `/api/status`、`/lab` 和 `/tree` 请求成功。
测试服务只在验证容器内短暂运行，结束即关闭。

平台可沿用管理员提供的启动命令；镜像保留 `/bin/bash` 默认命令，未添加固定 ENTRYPOINT，
支持平台覆盖启动命令。Jupyter 可执行程序位于 `/usr/local/bin`，镜像声明端口 8888。
如在独立 Docker 环境手动启动 JupyterLab，可执行：

```bash
docker run --rm -it --init \
  -p 127.0.0.1:8888:8888 \
  --mount type=bind,src=/绝对路径/工作目录,dst=/workspace \
  ghcr.io/libinghuang1994/qwen35-cpu-dev:0.2.0 \
  jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root
```

将挂载路径替换为 Docker 服务端的真实目录。手动启动保留 Jupyter 自动生成的 token，
从容器输出取得访问地址；平台的代理路径、认证、端口和挂载参数沿用平台配置。
这次仅增加已知的软件依赖，目标内网平台仍需实际拉取和启动验收。

系统包安装列表见 [apt-packages.txt](apt-packages.txt)。系统包从 Ubuntu 源解析，
每次构建的实际版本保存在镜像内 `/usr/local/share/qwen35-cpu-dev/packages.tsv`。
固定基础镜像和 CMake 不代表 apt 依赖的所有版本均被冻结；使用最终镜像摘要可以取得同一构建产物。

## 0.1.0 历史发布记录与基础开发用法

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

在仓库根目录可构建当前的 Jupyter 版本：

```bash
docker build --platform linux/amd64 \
  --file docker/qwen35-cpu-dev/Dockerfile.jupyter \
  --tag ghcr.io/libinghuang1994/qwen35-cpu-dev:0.2.0 \
  docker/qwen35-cpu-dev
```

GitHub Actions 的 `Build Qwen35 CPU development image` 工作流可手动触发，
也会在 `main` 分支的 Dockerfile、依赖清单、验证脚本、构建上下文规则或工作流自身发生变化时触发。
推送触发默认发布 `0.2.0`，手动触发可指定版本；后续正式更新时应同时调整默认版本。
原始 [Dockerfile](Dockerfile) 保留为 `0.1.0` 基础工具链的构建配方；当前工作流使用 `Dockerfile.jupyter`。
它在 `ubuntu-22.04` runner 构建 amd64 镜像，通过独立的离线容器验证后，
使用工作流临时令牌的 `packages: write` 权限发布至当前仓库所属账号的 GHCR。
工作流上传系统包及 Python 包版本清单、Jupyter 验证结果、镜像信息和发布日志作为构建记录。

当前流程不自动改变包的可见性，不添加定时任务，也不包含服务器部署操作。

## 官方来源

- Ubuntu：<https://hub.docker.com/_/ubuntu>
- CMake 3.31.6：<https://github.com/Kitware/CMake/releases/tag/v3.31.6>
- CMake 校验清单：<https://github.com/Kitware/CMake/releases/download/v3.31.6/cmake-3.31.6-SHA-256.txt>
- GHCR：<https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry>
