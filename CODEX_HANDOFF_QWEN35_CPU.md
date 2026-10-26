# Qwen3.5-4B CPU 部署交接

上下文快照日期：2026-10-26（Asia/Shanghai）。

本文件用于把当前 ChatGPT 会话中的部署任务交给本地 Codex。请先完整阅读，再接续工作。目标是使用 llama.cpp 在用户指定的 Ubuntu CPU 服务器上部署 Qwen3.5-4B；当前进行到环境检查和 CPU 版本编译的准备阶段。

## 1. 接手时先确认的事项

- 已确认 CPU 硬件和基线指令集符合候选构建要求。
- 尚未收到工具链版本、依赖安装、源码下载、构建完成或模型推理的结果。本文中的安装和编译命令是候选方案，不能记为已执行。
- 先确定 Codex 当前运行的电脑是否就是目标服务器。若不是，先准备供目标服务器执行的检查和构建脚本，或者使用用户已经提供并授权的连接方式。
- 用户提供的终端主机名不是 SSH 连接配置。没有提供 SSH 地址、端口、密钥或现成连接。不要猜测它们。
- 当前接续重点是第 1、2 步。权重下载、API 启动和性能调优属于后续阶段。
- 用中文与用户沟通，依据实际输出推进。保留已确认事实，无需反复让用户粘贴同一份硬件信息。

## 2. 用户目标及已讨论的整体流程

最终目标：CPU 运行 llama.cpp，加载 Qwen3.5-4B，并提供可供业务脚本调用的推理服务。

已讨论的流程：

1. 检查 CPU 拓扑、进程可用资源、编译器及构建工具。
2. 构建 CPU 版 llama-cli、llama-server、llama-bench。
3. 准备来源明确的 Qwen3.5-4B GGUF 权重。
4. 跑通单实例、单请求，核对中文输出、对话模板、思考模式。
5. 启动 llama-server，验证 HTTP API。
6. 比较线程数、NUMA、并发、量化精度，最后固定服务配置。

当前按纯文本推理规划；用户尚未提出图像或视频输入要求。

Docker 镜像可选，已建议首先原生部署。若后续发现用户已有容器运维要求，可调整；不要把 Docker 作为必需条件。

## 3. 用户实际提供的服务器信息

以下是用户终端输出中的事实；数值反映采集时状态。

| 项目 | 用户提供的信息 |
|---|---|
| 架构 | x86_64，支持 32-bit / 64-bit 运行模式 |
| 操作系统 | Ubuntu 20.04.6 LTS |
| 内核 | 5.15.0-119-generic |
| CPU 型号 | Intel(R) Xeon(R) Gold 6448H |
| CPU 插槽数 | 2 |
| 每插槽物理核心数 | 32 |
| 每核心硬件线程数 | 2 |
| 总物理核心数 | 64 |
| 在线逻辑 CPU | 128，编号 0–127 |
| NUMA 节点数 | 2 |
| NUMA node0 CPU | 0-31,64-95 |
| NUMA node1 CPU | 32-63,96-127 |
| NUMA 距离矩阵 | 本地 10，跨节点 21 |
| 总内存 | 约 1.0 TiB |
| 当时可用内存 | 约 901 GiB |
| Swap | 0 B |
| HugePages_Total | 0 |
| lscpu 汇总缓存 | L1d 3 MiB，L1i 2 MiB，L2 128 MiB，L3 120 MiB |
| 频率快照 | CPU MHz 2400.000，最小 800 MHz，最大 4100 MHz |
| 终端提示符中的用户 | root |
| 终端提示符中的主机名 | huanglibing3-specforge-train-eagle3 |
| 用户当时工作目录 | /mnt/huanglibing3 |
| numactl | 执行 numactl --hardware 返回“命令未找到” |

Intel 官方资料将 6448H 列为第四代 Xeon Scalable / Sapphire Rapids；单颗 32 核、64 线程，基础频率 2.40 GHz，最高睿频 4.10 GHz，并支持 AMX。来源见末尾。

### 3.1 已确认的关键指令集

候选 AVX-512/VNNI 基线所需标志均已出现：

~~~text
sse4_2 avx avx2 fma f16c bmi2
avx512f avx512cd avx512dq avx512bw avx512vl avx512_vnni
~~~

用户还提供了以下标志：

~~~text
avx_vnni avx512_bf16 avx512vbmi avx512_vbmi2
avx512_fp16 amx_tile amx_bf16 amx_int8
~~~

### 3.2 已澄清的采集问题

- lscpu 使用中文字段，英文 grep 只能匹配部分缓存行。需要英文格式时用 LC_ALL=C lscpu。
- ARM 检测正则中的裸 bf16 匹配到了 avx512_bf16 / amx_bf16 子串。该机器明确为 x86_64。
- numactl 缺失属于工具未安装；NUMA 硬件已经由 lscpu 识别。
- 单次 2400 MHz 读数不能证明热降频或功耗限频；4.10 GHz 也不是全核持续频率保证。
- lscpu 缓存数据是汇总值，不能解释成单个核心拥有 120 MiB L3。
- 早先采集中的“已插 DIMM 数 0”不能用来推断实际内存条、通道占用和运行带宽。

## 4. 尚未确认的状态

接手者必须继续核实：

1. GCC、G++、CMake、Make、Git、Python 的路径和版本。
2. 当前进程的 CPU / NUMA 亲和性，以及必要时的 cgroup CPU quota 和内存限制。
3. 当前环境是物理宿主机、容器还是其他受调度环境。
4. 是否已经存在用户执行前轮命令后产生的部署目录、源码、venv、构建产物和日志。
5. 实际可用的磁盘空间及项目保存位置。
6. AMX 的内核运行时支持、进程权限和实际执行情况。

以下事项没有完成证据：

- 安装 numactl 或其他依赖。
- 创建专用构建工具 venv，安装 CMake。
- 下载 llama.cpp 源码。
- 执行 CMake 配置和编译。
- 三个工具的启动检查或动态库检查。
- 下载 GGUF、加载模型、启动 API、测量吞吐量。

128 个在线逻辑 CPU 和约 1 TiB 内存是用户看到的系统信息，不等于当前进程一定获得全部资源。root 提示符也不能替代实际环境和配额检查。

## 5. 已提出的构建方案

这些是候选方案，应结合目标环境和实际源码核对；不是已经执行成功的状态。

| 项目 | 候选设置 |
|---|---|
| 引擎 | llama.cpp |
| 固定源码版本 | v0.7.0 |
| 原建议工作目录 | $HOME/qwen35-cpu |
| 源码子目录 | llama.cpp-v0.7.0 |
| 构建目录 | build-cpu-avx512 |
| 构建工具环境 | build-tools |
| CMake | cmake==3.31.6 |
| 编译器 | 优先检查系统 GCC/G++；原方案显式使用 /usr/bin/gcc 和 /usr/bin/g++ |
| 优化模式 | Release |
| 初始 CPU 路径 | AVX-512 + AVX-512 VNNI |
| 编译并行度 | 16 个编译任务，仅为起步值，不是推理线程数 |
| 构建目标 | llama-cli、llama-server、llama-bench |

本轮官方发布页核查时 v0.7.0 是 Latest。交接之后应把它作为已选版本，不必为了“最新”自动切到其他版本。下载后记录实际完整提交号。

原建议目录尚未确认存在。用户工作目录 /mnt/huanglibing3 也没有被确认是持久化卷；可以依据实际环境选择合适项目目录。若调整路径，统一修改所有源码、工具和日志路径。

### 5.1 选择这些配置的原因

- v0.7.0 根 CMakeLists.txt 声明最低 CMake 3.14，但 server/cli 依赖的 scripts/ui-assets.cmake 要求 CMake 3.18。不能只看根文件就认定系统 CMake 3.16 足够。
- 在独立 venv 中安装 CMake 3.31.6，并通过完整路径调用，避免混用旧 CMake。
- 源码使用 C++17。GCC 9.x 是 AVX-512/VNNI 基线的候选，不应宣称已经在用户服务器实测通过，也不应无依据地把 GCC 12 当作整个项目的硬门槛。
- x86 构建逻辑在 GGML_NATIVE=ON 时加入 -march=native；显式 AVX/AMX 开关位于另一分支。因此 NATIVE=ON 加 AMX=OFF 不能可靠保证没有启用 AMX。
- 首轮 GGML_NATIVE=OFF，显式启用 AVX-512/VNNI；关闭 AMX、AVX-512 BF16、AVX-VNNI、VBMI。AVX-512 VNNI 与 AVX-VNNI 是两个不同选项。
- 候选配置不接入额外 BLAS，先测量 CPU 后端基线。
- LLAMA_OPENSSL=OFF：后续以外部下载工具获取模型，使用本地 GGUF 和普通 HTTP API。llama.cpp 内部 HTTPS 下载不可用，系统 curl 不受影响。此版本的 HTTPS 路径涉及 OpenSSL 3，旧 LLAMA_CURL 选项已弃用。
- 关闭 Web UI 构建和预编译 UI 下载；保留 HTTP API 和 CLI。没有嵌入式 UI 资源的提示是这套配置的预期情况。
- AMX 标志不证明应用已使用 AMX。Linux 相关权限按进程管理；单独探针成功不会替后续独立启动的 llama-server 持久开启 AMX。
- 不能仅凭内核版本字符串 5.15 断言 AMX 不可用，发行版可能回移支持；也不能以更新容器用户态代替宿主内核能力验证。

## 6. 直接下一步

先确认执行位置。如果当前 Codex 不在目标服务器，以下检查应提供给用户在目标服务器上执行，或者通过已有且获授权的连接执行。不要把本地电脑的输出当成服务器结果。

### 6.1 只读环境检查

~~~bash
hostname
pwd
uname -r
cat /etc/os-release

for tool in gcc g++ cmake make git python3; do
    if command -v "$tool" >/dev/null 2>&1; then
        printf '\n[%s]\n' "$tool"
        command -v "$tool"
        "$tool" --version | head -n 1
    else
        printf '\n[%s] NOT INSTALLED\n' "$tool"
    fi
done

getconf GNU_LIBC_VERSION
nproc
awk '/^Cpus_allowed_list:|^Mems_allowed_list:/ {print}' /proc/self/status
cat /proc/self/cgroup

if command -v numactl >/dev/null 2>&1; then
    numactl --hardware
fi

if [ -x "$HOME/qwen35-cpu/build-tools/bin/cmake" ]; then
    "$HOME/qwen35-cpu/build-tools/bin/cmake" --version
fi

df -h "$HOME" /mnt/huanglibing3
~~~

如需解析容器配额，应根据 /proc/self/cgroup 和实际 cgroup 挂载位置读取对应限制，兼容 v1/v2。不要假设固定根路径总是当前进程的 cgroup。

SMT 配对尚未核实；需要精确线程绑定时再查看：

~~~bash
LC_ALL=C lscpu -e=CPU,CORE,SOCKET,NODE,ONLINE
~~~

### 6.2 检查项目现状

在既有用户工作目录和原建议目录中查看是否已有本任务文件、源码或构建结果。先读取已有状态，再决定新建或复用。不要删除已有目录以“从头再来”。

若当前环境尚不能访问目标服务器，生成便于用户执行的脚本和明确的运行说明，并据实际回传结果推进。

## 7. 候选安装和构建命令

本节保留前轮方案供接手者复用。执行前确认目标机器、工具版本、路径以及当前用户授权范围。不要因为本文件存在就假定所有命令已经运行。

### 7.1 基础依赖

用户提供的服务器提示符是 root。如果实际执行账户也是 root：

~~~bash
apt-get update
apt-get install -y \
    build-essential git python3 python3-venv numactl \
    pkg-config ca-certificates curl ripgrep
~~~

若实际为普通账户，依现有权限处理；依赖已满足时无需重复安装。

### 7.2 独立 CMake 和固定源码

下面按首次安装编写。已有相应目录时先检查并复用，不覆盖已有内容。

~~~bash
(
    set -euo pipefail

    QWEN_CPU_ROOT="$HOME/qwen35-cpu"
    QWEN_SRC="$QWEN_CPU_ROOT/llama.cpp-v0.7.0"

    mkdir -p "$QWEN_CPU_ROOT/logs"

    /usr/bin/python3 -m venv "$QWEN_CPU_ROOT/build-tools"
    "$QWEN_CPU_ROOT/build-tools/bin/python" -m pip install \
        --only-binary=:all: "cmake==3.31.6"
    "$QWEN_CPU_ROOT/build-tools/bin/cmake" --version

    git clone --depth 1 --branch v0.7.0 \
        https://github.com/ggml-org/llama.cpp.git "$QWEN_SRC"

    git -C "$QWEN_SRC" rev-parse HEAD \
        | tee "$QWEN_CPU_ROOT/logs/source-commit.txt"
    git -C "$QWEN_SRC" describe --tags --exact-match
)
~~~

### 7.3 AVX-512/VNNI 基线构建

~~~bash
(
    set -euo pipefail

    QWEN_CPU_ROOT="$HOME/qwen35-cpu"
    QWEN_SRC="$QWEN_CPU_ROOT/llama.cpp-v0.7.0"
    QWEN_BUILD="$QWEN_SRC/build-cpu-avx512"
    QWEN_CMAKE="$QWEN_CPU_ROOT/build-tools/bin/cmake"

    mkdir -p "$QWEN_CPU_ROOT/logs"
    cd "$QWEN_SRC"

    "$QWEN_CMAKE" -S . -B "$QWEN_BUILD" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER=/usr/bin/gcc \
        -DCMAKE_CXX_COMPILER=/usr/bin/g++ \
        -DCMAKE_C_FLAGS="" \
        -DCMAKE_CXX_FLAGS="" \
        -DGGML_NATIVE=OFF \
        -DGGML_AVX2=ON \
        -DGGML_FMA=ON \
        -DGGML_F16C=ON \
        -DGGML_BMI2=ON \
        -DGGML_AVX512=ON \
        -DGGML_AVX512_VNNI=ON \
        -DGGML_AVX512_VBMI=OFF \
        -DGGML_AVX512_BF16=OFF \
        -DGGML_AVX_VNNI=OFF \
        -DGGML_AMX_TILE=OFF \
        -DGGML_AMX_INT8=OFF \
        -DGGML_AMX_BF16=OFF \
        -DGGML_CUDA=OFF \
        -DGGML_VULKAN=OFF \
        -DGGML_SYCL=OFF \
        -DGGML_BLAS=OFF \
        -DGGML_OPENMP=ON \
        -DLLAMA_OPENSSL=OFF \
        -DLLAMA_BUILD_TESTS=OFF \
        -DLLAMA_BUILD_EXAMPLES=OFF \
        -DLLAMA_BUILD_APP=OFF \
        -DLLAMA_BUILD_TOOLS=ON \
        -DLLAMA_BUILD_SERVER=ON \
        -DLLAMA_BUILD_UI=OFF \
        -DLLAMA_USE_PREBUILT_UI=OFF \
        2>&1 | tee "$QWEN_CPU_ROOT/logs/configure-avx512.log"

    "$QWEN_CMAKE" --build "$QWEN_BUILD" \
        --parallel 16 \
        --target llama-cli llama-server llama-bench \
        2>&1 | tee "$QWEN_CPU_ROOT/logs/build-avx512.log"
)
~~~

如果实际 CPU 配额、编译器路径或现有环境与假定不同，先相应调整参数。更换编译器或关键后端时，使用独立构建目录，避免混用旧缓存。

### 7.4 启动与依赖检查

~~~bash
QWEN_BIN="$HOME/qwen35-cpu/llama.cpp-v0.7.0/build-cpu-avx512/bin"

"$QWEN_BIN/llama-cli" --version
"$QWEN_BIN/llama-server" --version
"$QWEN_BIN/llama-bench" --help
ldd "$QWEN_BIN/llama-server"

rg \
    '^(CMAKE_BUILD_TYPE|GGML_NATIVE|GGML_AVX512|GGML_AVX512_VNNI|GGML_AMX_TILE|GGML_AMX_INT8|GGML_AMX_BF16|GGML_CUDA|LLAMA_OPENSSL):' \
    "$HOME/qwen35-cpu/llama.cpp-v0.7.0/build-cpu-avx512/CMakeCache.txt"
~~~

本阶段成功标准：

- 构建命令正常结束，三个目标产物存在。
- CLI 和 server 能打印版本，bench 能打印帮助。
- 动态依赖无缺失。
- 实际编译参数符合基线设置；需要确认 ISA 时检查 compile_commands.json，不能仅依赖缓存中的意向设置。
- 保存真实源码提交号、配置日志和构建日志。

这些检查只证明程序构建和启动，不证明 Qwen3.5-4B 已成功加载或达到了性能目标。

## 8. 后续阶段保留事项

完成第 1、2 步后再推进：

- 选择并记录 GGUF 的来源、文件名、版本和校验信息。
- 前轮建议以 Q8_0 跑通；若关心与高精度输出的一致性，可增加 BF16/F16 参考；若追求速度，再比较 Q4_K_M。它们不是已验证的最终选择。
- 从单实例、单请求和适中的上下文长度起步；4K/8K 是建议起点。
- 核对模型对话模板和思考模式。不要直接沿用旧 Qwen 模型的 /nothink 假设。
- 先测实际输入处理、生成速度和输出结果，再调整线程与并发。
- NUMA 单节点基线、跨节点单实例、每节点一个实例都属于待比较方案，不预先认定某种一定最快。
- 不把 128 当作默认最佳推理线程数；编译并行度也不等于推理线程数。
- 用户尚未指定最终量化精度、吞吐/延迟验收阈值、服务监听地址或部署运维方式。

## 9. 工作记录方式

每次有实际进展后，更新本文件中的当前状态，或者在同目录维护简短状态记录，至少包括：

- 已执行命令及关键结果。
- 所在机器和实际工作目录。
- 源码提交号、编译器和 CMake 版本。
- 产物与日志路径。
- 当前阻塞点和下一步。

保持“用户提供的事实”“新实测结果”“待验证方案”的区别。读取项目中现有 AGENTS.md 等规则；这份交接文件用于补充项目状态。

## 10. 参考资料

以下资料来自前轮部署讨论和本轮转移方式核查。具体软件行为以所选源码版本和目标机器结果为准。

### 部署资料

- [Intel Xeon Gold 6448H 官方规格](https://www.intel.com/content/www/us/en/products/sku/232391/intel-xeon-gold-6448h-processor-60m-cache-2-40-ghz/specifications.html)
- [llama.cpp v0.7.0 发布页](https://github.com/ggml-org/llama.cpp/releases/tag/v0.7.0)
- [v0.7.0 构建说明](https://github.com/ggml-org/llama.cpp/blob/v0.7.0/docs/build.md)
- [v0.7.0 CPU CMake 配置](https://github.com/ggml-org/llama.cpp/blob/v0.7.0/ggml/src/ggml-cpu/CMakeLists.txt)
- [v0.7.0 UI 资源脚本](https://github.com/ggml-org/llama.cpp/blob/v0.7.0/scripts/ui-assets.cmake)
- [v0.7.0 cpp-httplib 构建配置](https://github.com/ggml-org/llama.cpp/blob/v0.7.0/vendor/cpp-httplib/CMakeLists.txt)
- [CMake 3.31.6 安装包](https://pypi.org/project/cmake/3.31.6/)
- [Linux XSTATE 与 AMX 文档](https://docs.kernel.org/arch/x86/xstate.html)
- [Qwen3.5-4B 官方模型卡](https://huggingface.co/Qwen/Qwen3.5-4B)
- [llama.cpp server 文档](https://github.com/ggml-org/llama.cpp/blob/v0.7.0/tools/server/README.md)

### Codex 接续资料

- [Codex CLI](https://learn.chatgpt.com/docs/codex/cli)
- [CLI 命令与会话恢复](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
- [AGENTS.md 项目指令](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [桌面版项目与聊天](https://learn.chatgpt.com/docs/projects)
- [其他代理导入功能的适用范围](https://learn.chatgpt.com/docs/import)

## 11. 可直接使用的接续指令

请完整读取本文件，接续 llama.cpp 部署 Qwen3.5-4B 的任务。先确认当前执行环境与目标服务器的关系，再补查工具链、进程可用资源和已有项目状态。根据实际结果推进环境准备与 CPU 构建；若当前不在目标服务器且没有已提供的连接方式，就先生成供目标服务器执行的脚本。不要把文档里的建议视为已经执行。完成实际操作后记录结果、日志位置和下一步。

