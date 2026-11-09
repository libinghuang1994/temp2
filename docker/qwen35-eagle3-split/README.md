# EAGLE3 分批下载：四个小镜像

原版 `eagle3-qwen35-4b-v1` 的压缩数据层为 764,731,594 字节。为绕过疑似单次大文件下载问题，将**同一已校验数据层按字节切为四份**，每份分别放入一个独立的 scratch 数据镜像。前三份各 200 MiB，第四份约 129.3 MiB；压缩镜像层会有少量封装开销，发布时要求每个 blob 小于 201 MiB，也小于十进制 300 MB。

这是 AICR 当前故障的分发绕行方案，300 MiB 限制尚未确认。四份集齐后恢复原镜像中的全部文件，含原始 BF16、F16 GGUF、tokenizer、转换器、许可证和验证记录；不会重新转换或修改模型。恢复产物为文件目录，无须重新 `docker load` 大镜像。

发布状态：构建和验证中，最终状态及每份固定摘要将记录在 `release-200m-v1.json`。

## 1. 按批次拉取

沿用原有镜像路径，仅更换 tag。在能使用 Docker、能拉取 AICR 镜像的机器上逐条执行；也可每次只执行一条：

```bash
docker pull --platform linux/amd64 aicr.byd.com/ghcr.io/libinghuang1994/qwen35-cpu-dev:eagle3-qwen35-4b-v1-200m-part01
docker pull --platform linux/amd64 aicr.byd.com/ghcr.io/libinghuang1994/qwen35-cpu-dev:eagle3-qwen35-4b-v1-200m-part02
docker pull --platform linux/amd64 aicr.byd.com/ghcr.io/libinghuang1994/qwen35-cpu-dev:eagle3-qwen35-4b-v1-200m-part03
docker pull --platform linux/amd64 aicr.byd.com/ghcr.io/libinghuang1994/qwen35-cpu-dev:eagle3-qwen35-4b-v1-200m-part04
```

外网来源是相同仓库与 tag：`ghcr.io/libinghuang1994/qwen35-cpu-dev:eagle3-qwen35-4b-v1-200m-part01` 至 `part04`。目标 AICR 是否已同步新 tag，需要内网验证；出现 `manifest unknown` 时，请管理员按完整名称同步这四个新 tag。

若平台只提供镜像导入界面，分别导入四个 tag，再由有 Docker 的管理员执行下面的提取。分片镜像没有 Shell，不要运行 `docker run`。

## 2. 提取四份到同一个目录

在四份均已拉取的机器执行。`docker create` 只创建停止状态的容器，不执行 `/data-only`；`docker cp` 可读取停止容器，见 [Docker 文档](https://docs.docker.com/reference/cli/docker/container/cp/)。

```bash
(
    set -euo pipefail
    mkdir -p ./qwen35-eagle3-parts
    part_container=''
    trap 'if test -n "$part_container"; then docker rm "$part_container" >/dev/null; fi' EXIT
    for part in 01 02 03 04; do
        image="aicr.byd.com/ghcr.io/libinghuang1994/qwen35-cpu-dev:eagle3-qwen35-4b-v1-200m-part${part}"
        part_container=$(docker create "$image" /data-only)
        docker cp "$part_container:/opt/qwen35-eagle3-split/." ./qwen35-eagle3-parts/
        docker rm "$part_container" >/dev/null
        part_container=''
    done
)
```

也可每次拉取后只提取相应一份，四份最后放在同一目录。各镜像中的 `SOURCE.json`、`PARTS.SHA256SUMS`、`reassemble.sh` 内容相同，合并目录时同名元数据可以覆盖；`layer.blob.part01` 至 `part04` 各不相同。把这个目录转入现有开发容器的持久挂载路径后，后续仅需 Bash、tar、sha256sum，不需 Docker 或网络。

## 3. 合并校验并导出草稿头

先预留约 2 GB 文件空间（分片约 765 MB、解包约 995 MB；不含 Docker 自身存储），解包目录必须是新目录：

```bash
bash ./qwen35-eagle3-parts/reassemble.sh ./qwen35-eagle3-restored
```

脚本依次验证四个分片 SHA256、合并后的原始层 SHA256、gzip/tar 解包、原有文件清单和固定 GGUF SHA256；任何失败均停止。看到 `RESULT=PASS` 后执行原有导出脚本，目标目录也必须不存在：

```bash
bash ./qwen35-eagle3-restored/opt/qwen35-eagle3-4b/export-head.sh \
  /mnt/huanglibing3/models/draft/Qwen3.5-4B-EAGLE3-v1
```

GGUF 最终路径：

```text
/mnt/huanglibing3/models/draft/Qwen3.5-4B-EAGLE3-v1/gguf/Qwen3.5-4B-EAGLE3-F16.gguf
```

GGUF 固定 SHA256：`1b76f2f3af3e9ce4fc7d240ff82b10ee9885fdd080390d1c3de0532ec292bf62`，477,099,552 字节。不要截断或直接拼接 GGUF；脚本拼接的是原始压缩层的四段。合并不经过 AICR，不会再次触发单次大对象下载。

## 来源与复现

原镜像摘要：`sha256:50a4f18e786aec5c9ffedc07403585fe251ba74638b72b9142c8e902bfa4d3e4`；原始压缩层 SHA256：`f5132305517a11cca973ef4afa7f5af85329710a439cb60c05a08d0290aff8be`，764,731,594 字节。模型、转换及 CPU 验证范围沿用[原版说明](../qwen35-eagle3-4b/README.md)；目标服务器 EAGLE3 完整生成、AMX、并发24接受率和净吞吐仍未验收。

新目录中重做分片（默认匿名下载并校验固定原始层；`--layer` 可复用完整已下载文件）：

```bash
python3 docker/qwen35-eagle3-split/prepare.py --work-dir /tmp/eagle3-split-new
```

发布工作流在推送分片配方时触发：检查原始 manifest 和层、制作四个独立镜像、从最终四个镜像提取并恢复、验证所有文件及导出脚本，再推送并逐个匿名下载全部 blob 校验大小和 SHA256。原版 tag 保留。
