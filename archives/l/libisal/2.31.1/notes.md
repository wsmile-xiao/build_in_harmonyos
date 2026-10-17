# libisal 2.31.1 适配笔记

## 上游概况

- Intel ISA-L（Intelligent Storage Acceleration Library），autoconf 包名
  `libisal`，tarball 名 `isa-l`。功能：CRC16/32/64、igzip（raw deflate /
  gzip / zlib 压缩）、RAID XOR/PQ 生成与校验、GF(2^8) 纠删码、mem 工具。
- v2.31.1 发布于 2025-01-08，release **无 dist 资产**，官方源只有 GitHub
  自动打包（含 configure.ac / Makefile.am / autogen.sh / **Makefile.unx +
  make.inc**，不含 configure）。
- 零外部依赖（W0 通过）：无 requirements，igzip CLI 只链接 libisal 本身。

## aarch64 支持分析（源码分析结论）

| 模块 | aarch64 实现 | 说明 |
|------|-------------|------|
| crc | crc/aarch64/*_pmull.S、*_crc_ext.S、*_mix_neoverse_n1.S + dispatcher | PMULL/CRC-ext/Neoverse 分派 |
| erasure_code | erasure_code/aarch64/*_neon.S、*_sve.S + dispatcher | NEON/SVE |
| raid | raid/aarch64/（base C + NEON） | |
| igzip | igzip/aarch64/*（NEON adler32、deflate 汇编）+ 全套 C 内核 | |
| mem | mem/aarch64/ | |

- 运行时分派：`include/aarch64_multibinary.h` 的**自修补蹦床**（非 ifunc），
  dispatcher 用 `getauxval(AT_HWCAP)` 读 HWCAP_PMULL/CRC32/ASIMD；无特性位
  回退 `_base` C 实现 → 任何 aarch64 CPU 都正确。
- dispatcher 里 `#if defined(__linux__)` 门控 getauxval；OHOS 原生编译定义
  `__linux__`；即使未定义也只是回退 C 实现。

## 构建方案：上游 Makefile.unx（真机实证路线）

**为什么放弃 autotools/bootstrap（第一版配方）**：真机（HMDFS）上
tool_requires 的 automake/autoconf/libtool 需要从源码构建，而工具包自身的
构建第一步 `autotools.configure()` 直接 exec configure 即触发
`/system/bin/sh: configure: Permission denied`（Error 126，HMDFS 拒脚本 exec）；
且 automake 构建依赖 conan perl/5.42.2，其 Cwd.so 在 HMDFS dlopen 失败；
ohpcd 制品仓亦无这些工具的预构建二进制（曾试 `conan download`，not found）。
系统侧只有 autoconf/autoreconf/m4/perl（hnp/bin），缺 automake/aclocal/libtoolize。

**Makefile.unx 方案**：上游维护的免 autotools 构建系统，`include` 与
autotools 完全相同的各模块 Makefile.am 源列表，按 `host_cpu=aarch64` 选
aarch64 源 + C 基础实现；`AS=$(CC) -D__ASSEMBLY__` 汇编 .S；目标：
`lib`（bin/isa-l.a）、`slib`（.so，带符号链）、`progs`（igzip CLI）、
`check`（构建并运行 16 个上游 check 测试）、`install`。

配方要点（真机注意事项）：
1. **`arch=aarch64 host_cpu=aarch64` 显式传入**：make.inc 的
   `arch ?= $(shell uname | grep -v Linux BSD)` 在 HarmonyOS 上会得到
   "HarmonyOS" 而非 aarch64。
2. **`-fno-integrated-as` 挂在 CC 里**（`CC="clang -fno-integrated-as"`）：
   52 个 aarch64 .S 用 `.req` 别名，clang 15 集成汇编器不支持（isa-l_crypto
   2.26 同款），走系统 GNU as 2.45（/data/service/hnp/bin）。make.inc 用
   `CFLAGS = ...` 普通赋值——命令行 CFLAGS 会整体覆盖丢掉 -I/-O2，而 CC 是
   `?=`，且 AS=$(CC)/LINK.o 都经由 CC 传导。
3. **AR=llvm-ar** 从 `tools.build:compiler_executables` conf 取（R33）。
4. **TMPDIR 指向 build/tmp**：make.inc 的汇编特性探测和 pthread 探测用
   mktemp，OHOS /tmp 只读。
5. 只做静态库（默认）：slib 目标带 `ln -f -s` 符号链，HMDFS 风险；CI 消费
   者按 -lisal 静态链接。打包手动 copy（lib/isa-l.a → lib/libisal.a、
   include/*.h → include/isa-l/、isa-l.h → include/、bin/igzip → bin/），
   不跑 `make install`（其 man/symlink 步骤无必要）。
6. 上游测试：`make check` 16 个（crc 4 + ec 4 + igzip 3 + mem 1 + raid 4）。

## test_package 已知答案值（全部可复算）

期望值按上游 crc_base.c / crc64_base.c 的参考表在本机 Python 复算（表解析
自源码），并与公开目录锚点值交叉验证：

| API（"123456789", init 0/1） | 期望值 | 锚点 |
|------|--------|------|
| crc16_t10dif | 0xD0DB | CRC-16/T10-DIF 目录值 |
| crc32_ieee | 0xFC891918 | CRC-32/BZIP2 目录值 ✓ |
| crc32_gzip_refl | 0xCBF43926 | zlib CRC-32 目录值 ✓ |
| crc32_iscsi（buf,len,init 签名） | 0x58E3FA20 | 上游 iscsi 参考表 |
| crc64_ecma_norm | 0x62EC59E3F1A4F00A | 上游表 + 算法 |
| crc64_jones_norm | 0xDCF90FB7D3A994F3 | 上游表 + 算法 |
| isal_adler32("Wikipedia",1) | 0x11E60398 | Wikipedia 示例值 ✓ |

另有 igzip 64 KiB 状态压缩/解压 round-trip（5 项断言）、raid xor_gen 校验、
gf_vect_mul vs 逐位 GF(2^8) 参考实现，共 13 项断言。

## 真机验证记录

- 设备：LAN 直连 10.62.178.77:2222（HarmonyOS，hnp 工具链在
  /data/service/hnp/bin，452 个工具；GNU as 2.45；Perl 5.42.0）。
  frp 那台负载 23-25 不用。裸 SSH PATH 不含 hnp/bin——命令前必须
  `export PATH=/data/service/hnp/bin:$HOME/usr/local/bin:$HOME/.local/bin:$PATH`。
- 隔离作业：`ohos-prepare-isolated-conan-job.sh --user libisal --job libisal-2311
  --package archives/l/libisal/2.31.1 --repo-url <fork> --branch feat/libisal-2.31.1`；
  隔离 conan-home 需手动补 settings.yml/remotes.json/profiles（含 default），
  且 ohos-aarch64 profile 要加 `os.version=6.0`（否则 settings.os.version
  value not defined）。
- 第一轮失败：automake/1.18 从源码构建挂 Error 126（见上）→ 改 Makefile.unx。

## 风险与回退

- 若 `-fno-integrated-as` 找不到 `as`：worker 无 binutils → 需给 52 个 .S
  打 patch 去 `.req`（量大，不优先）。
- 若 `make check` 某测试因平台差异失败：记录豁免（MANIFEST），逐个分析。
- mem_zero_detect 不在公开安装头文件里（mem_routines.h 无此声明），
  test_package 不测它。
