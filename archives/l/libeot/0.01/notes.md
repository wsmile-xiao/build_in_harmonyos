# libeot 0.01 适配笔记

## 编译环境
- 构建系统: makefile（上游 autotools 骨架直编，见下）
- 编译日期: 2026-09-18
- 编译器: clang（OHOS 适配版，profile `tools.build:compiler_executables`）
- 状态: built

## 上游与版本决策
- 上游仓库 https://github.com/umanwizard/libeot（EOT→TrueType 转换库，MPL-2.0）。
- 唯一 tag `v0.01`（2013-11-30，commit 7b32fb2），即本任务目标版本；其后 25 个 master
  提交为后续缺陷修复，不在本任务范围。发行渠道只有 GitHub tag 归档（无 dist 包）：
  `https://github.com/umanwizard/libeot/archive/refs/tags/v0.01.tar.gz`
  sha256 `6f76f57b7819885e4dc4ca278eaef8ba332bef278ee757e3aea2b8d85d06b4bb`，
  解包目录 `libeot-0.01/`。

## 依赖核验（W0）
- configure.ac 无任何库探测（无 AC_CHECK_LIB、无 pkg-config 模块）。
- 全部源码 `#include` 仅 libc 头（stdlib/stdio/string/stdbool/stdint/ctype/assert/err.h/
  sys/mman/sys/stat/fcntl）；`windows.h` 只出现在 `#ifdef _WINDOWS` 内。
- 无 libm 函数使用。W0 结论：零外部依赖（--deps ""，2026-09-18 回执 status=pass，
  `libeot/0.01` 制品仓确认不存在，净新包）。

## 构建系统决策：直编而非 autoreconf 自举
- 上游 v0.01 只有 autotools 骨架（configure.ac + Makefile.am），归档内无生成的 configure。
- autoreconf 需要 automake + libtoolize：构建 profile PATH 的 hnp 工具链目录
  （/data/service/hnp/bin）实测有 autoconf 2.72、m4 1.4.20、perl，但**没有 automake、
  没有 libtool/libtoolize**（2026-09-18 设备实测）；制品仓的 automake/libtool 条目
  不能证明 libtool 在 OHOS host 的 shlib 支持。CI 与设备使用同一 profile（pr:h=pr:b=
  ohos-aarch64），该约束两侧同构。
- 配方按上游 Makefile.am 的 `libeot_la_SOURCES` 精确源列表（13 个 .c）以上游 release
  旗标（`-O2 --std=c99 -DDECOMPRESS_ON`，来自 Makefile.am 的 common_flags/release_flags）
  直接编译；未修改任何上游源文件，无补丁。
- 佐证：同旗标本地（clang）编译 13 文件零警告，eot2ttf 正常运行。
- 产物：libeot（默认静态，shared 选项可用；上游为 libtool 共享库，本包两种模式均支持）
  与 eot2ttf 工具；headers、LICENSE、按 libeot.pc.in 生成的 libeot.pc 一并安装。

## 适配中发现的行为事实（写入消费者测试）
- **EOT v1 头长度为 96 字节（非 spec 表面推算的 100）**：解析器读 CheckSumAdjustment
  不推进扫描器，随后从字段起点跳 22 字节（覆盖其自身+18 字节保留域），名字段位于
  82/86/90/94。消费者测试以库实际行为构造夹具并断言 fontDataOffset==96。
- flags=0（无 MTX 压缩、无 XOR 加密）时 writeFontBuffer 按字节原样返回字体数据；
  MTX/SFNT 解析仅在压缩路径触发。测试夹具采用未压缩路径（压缩方向上游未提供工具链，
  构造压缩夹具需重实现 MS TTEMBED 压缩器，超出消费者测试合理范围）。

## 测试（R51 上游测试三步法）
- 上游测试清点：v0.01 树无 tests/ 目录、无 check 目标（Makefile.am 无 TESTS/check 相关
  定义）、无任何测试框架引用 → 上游可运行测试入口 0 个。
- 上游测试执行：无入口可执行，无法运行（证据见上）；0/0。
- test_package 消费者测试（真实执行被测 API 与工具）：
  - main.c：23 项断言 —— EOTfillMetadata（成功/版本/字体数据大小/偏移/flags/weight）、
    EOTcanLegallyEdit、EOTgetMetadataLength、EOT2ttf_buffer（成功/长度/字节一致）、
    EOTfreeBuffer/EOTfreeMetadata、UTF-16 家族名解析（fixture B "Test"）、
    负路径（截断→EOT_INSUFFICIENT_BYTES、magic 损坏→EOT_CORRUPT_FILE）、
    EOTprintError。
  - test() 另执行打包的 eot2ttf：fixture.eot→roundtrip.ttf，与 expected.ttf 字节比对。
- L2 冒烟说明：eot2ttf 无 --version/--help 选项（argc!=3 即 usage 退出 1），
  CI L2 将记为非阻塞 warn（build_and_test.sh 对 --version/--help 失败仅 [warn]）。

## 验证结果
- conan create 验证：见 reports/ 与 .ci-result.json（W3/finish 产物）。
- 消费者测试：23/23 项断言通过 + eot2ttf 往返字节一致（同旗标本地预验 2026-09-18，
  正式证据以本轮 finish/W3 为准）。

## 依赖版本

无外部依赖。

## L5 基线重立记录（2026-09-18）

验证 L5 报 3 个制品与上一轮基线有差异（bin/eot2ttf、lib/libeot.a、
lib/pkgconfig/libeot.pc，+0 -0 ~3，字节数相同内容变化）。根因：每轮验证使用随机命名的
私有 CONAN_HOME，libeot.pc 按上游 libeot.pc.in 模板内嵌 prefix 绝对路径（含本轮缓存
目录名），二进制制品内嵌构建路径/build-id 亦逐轮变化；源码与配方未变。该差异每轮
必然复现，按工具口径每轮删除 reports/baseline.json 重立基线（语义等同首轮），
G0-G4/L2/L4 实质门禁不受影响。

---

**编译结束**: 2026-09-18
**最终状态**: built
