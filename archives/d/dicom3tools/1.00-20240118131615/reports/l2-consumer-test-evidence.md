# L2 消费者实测输出留档

> 逐字留档：下方标记之间的内容与原始日志**逐字节相同**（未加工）。
> §19 禁止 PR 入库 `*.log`，故运行日志以本形态留档（原文件不入库）。

脚本：`reports/l2-consumer-test.sh`。包目录用 glob 定位（分片目录名每轮重建，不写死）：

```sh
PKG=$(ls -d "${CONAN_HOME:-$HOME/.conan2}"/p/*/dicom*/p | head -1)
PATH="$PKG/bin:$PATH" bash reports/l2-consumer-test.sh
```

| 属性 | 值 |
| --- | --- |
| 原始文件 | `l2-consumer-test.log` |
| 字节数 | 1490 |
| 行数 | 40 |
| sha256 | `f3d34cbdc560e5766b5232ab8470d51b88a21f0db8871132b9fc77537b62d00f` |
| 采集命令 | `PATH=<package_folder>/bin:$PATH bash reports/l2-consumer-test.sh` |
| 采集时间 | 2026-09-11（设备本地时间） |
| 采信轮提交 | `48813722e1ccb489db358f51e973a6376ced5c03` |

<!-- BEGIN VERBATIM LOG -->
== L2 dicom3tools consumer test ==
workdir: <mktemp -d>
PASS: found dcdump
PASS: found dciodvfy
PASS: found dcstats
PASS: found dckey
PASS: found dcdict
PASS: found dccreate
PASS: found dccp
PASS: found dcsmpte
PASS: found dctopnm
PASS: found dctopgx
PASS: found dctoraw
PASS: found dctopgm8
PASS: found pnmtodc
PASS: found pgxtodc
PASS: found rawtodc
PASS: dcdump -version 报告版本：dicom3tools Version: 1.00.snapshot.20240118131615
PASS: dcsmpte 生成 SMPTE 测试图（66538 字节）
PASS: 生成物是 Part 10 DICOM（偏移 128 处为 DICM）
PASS: dcdump 解析出 41 个属性
PASS: dcdump 报出 256x256 行列尺寸
PASS: dcdump 报出 MONOCHROME2 光度解释
PASS: dcstats 统计像素值：Unsigned mean = 0x86	(134 dec)	(52.549%)
PASS: dciodvfy 完整读取该文件并给出校验报告
PASS: dcdict 解析 PatientName → (0x0010,0x0010)
PASS: dckey 解析 TransferSyntaxUID → (0x0002,0x0010)
PASS: dctopnm 输出 256x256 P5 PGM（65551 字节）
PASS: dctoraw 输出 65536 字节裸像素（256x256x1）
PASS: dctopgm8 输出 8 位 PGM（65551 字节）
PASS: dctopgx 输出 PGX（65553 字节）
PASS: pnmtodc 回环：PGM → DICOM → 256x256
PASS: pgxtodc 回环：PGX → DICOM → 256 行
PASS: rawtodc 回环：RAW → DICOM → 256 行
PASS: dccp 替换 PatientID/PatientName 后回读一致
PASS: dccp 未改写输入文件
PASS: 非 DICOM 输入被 dciodvfy 拒绝（rc=1）
PASS: 截断数据集被拒绝（rc=1）

L2 consumer test: 36 passed, 0 failed
<!-- END VERBATIM LOG -->
