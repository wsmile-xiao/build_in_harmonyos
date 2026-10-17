# libisal

**Intel ISA-L（Intelligent Storage Acceleration Library）** — 面向存储与数据完整性的加速函数库：CRC16/32/64（T10-DIF、IEEE、iSCSI、ECMA/ISO/Jones/Rocksoft）、igzip 压缩（raw deflate / gzip / zlib，流式与一次性接口）、RAID XOR/PQ 生成与校验、GF(2^8) 纠删码。aarch64 平台上游原生提供 NEON/SVE/CRC-extension 实现，运行时按 HWCAP 特性自动分派，无特性位时回退可移植 C 实现。

- 上游仓库：https://github.com/intel/isa-l
- 许可证：BSD-3-Clause
- 姊妹包：isa-l_crypto 2.26（已在库）

## 产物

| 产物 | 说明 |
|------|------|
| `lib/libisal.a`（默认）/ `lib/libisal.so.2.0.31`（shared 选项） | 主库，链接名 `-lisal` |
| `include/isa-l/*.h` + `include/isa-l.h` | 公开头文件（`#include <isa-l/crc.h>` 风格） |
| `lib/pkgconfig/libisal.pc` | pkg-config 描述 |
| `bin/igzip` | gzip 压缩命令行工具（类似 gzip，多线程友好） |

## OHOS 适配要点（2.31.1）

- 官方 tag 源码包不含 configure（release 无 dist 资产），且 automake/
  autoconf/libtool 工具包无法在 HMDFS 真机上构建 → 使用**上游自带
  Makefile.unx + make.inc**（include 同一套 Makefile.am 源列表，
  host_cpu=aarch64 选 NEON/SVE 源，`AS=$(CC) -D__ASSEMBLY__`）。
- 52 个 aarch64 .S 使用 `.req` 寄存器别名，clang 15 集成汇编器不支持 →
  `-fno-integrated-as` 挂在 CC 上走系统 GNU as（与 isa-l_crypto 2.26 同款）。
- multibinary 运行时分派是自修补蹦床 + getauxval(AT_HWCAP)（非 ifunc），
  OHOS 友好；无 PMULL/CRC32 特性位时回退基础 C 实现。
- 上游 `make check` 16 个测试在 build() 内执行；test_package 13 项断言
  （CRC/Adler 已知答案 + igzip round-trip + xor_gen + gf_vect_mul）。
- 纯静态库（-lisal）+ bin/igzip CLI；打包手动 copy，不依赖 make install。
