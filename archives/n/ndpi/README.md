# nDPI

nDPI 是 ntop 维护的开源深度包检测（Deep Packet Inspection）库，OpenDPI 的超集，用于流量协议识别与分类。

## 功能概述

- 基于数据包内容与行为的协议识别（数百种协议，运行时通过 `ndpi_get_num_protocols()` 查询）
- 流（flow）粒度的检测状态机：`ndpi_detection_process_packet()`
- 风险/类别/指纹（JA4、TCP 指纹、nDPI 指纹）等元数据能力（5.0 新增统一指纹与协议栈概念）
- 附带示例工具 `ndpiReader`（pcap 离线分析）与上游 pcap 回放测试套件

## OHOS 适配

- **构建系统**：Autotools。GitHub archive tarball 不含预生成的 `configure`，配方在 `build()` 中执行 `autoreconf -fiv`（与 aircrack 1.7 相同模式），`tool_requires` 固定 `automake/1.18` 与 `libtool/2.5.4`。
- **HMDFS 兼容**：沿用已验证模式——`configure` 的 mktemp/umask 指向 `${TMPDIR:-/tmp}`、pwd 判定回退 `$PWD`、config.guess/config.sub 补充 HarmonyOS 识别、`make install` 使用 install-shim（chmod/hardlink 不可用环境）。
- **依赖链**：仅 `libpcap/1.10.6`（已发布）。`json-c` 在制品仓尚无 published 版本，故不声明；上游 `configure` 在缺 json-c 时自动禁用 `tests/unit`，`make check` 仍运行 `tests/do.sh`（pcap 回放）与 `tests/do-dga.sh`（DGA 准确率门禁），见版本级 notes 的上游测试审计。
- **交付物裁剪**：`make install` 会同时安装示例 `bin/ndpiReader` 与 `share/ndpi` 数据；配方在 `package()` 后移除这两处，仅保留库（`lib/libndpi.*`）、头文件（`include/ndpi`）与 `lib/pkgconfig/libndpi.pc`，保持纯 `library` 包（无需 commands.json）。

## 依赖关系

- 编译依赖：`libpcap/1.10.6`（`example/ndpiReader` 与 `tests/do.sh` 必需）
- 构建工具：`automake/1.18`、`libtool/2.5.4`（`tool_requires`，autoreconf 用）
- 可选（上游自动探测，OHOS 默认关闭）：`json-c`（单测）、`pcre2`、`maxminddb`、`rrd`、`nBPF`

## 参考资料

- 官网：https://www.ntop.org/products/deep-packet-inspection/ndpi/
- 源码：https://github.com/ntop/nDPI
- 版本：https://github.com/ntop/nDPI/releases/tag/5.0
