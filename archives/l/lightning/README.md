# GNU lightning

运行时代码生成（JIT）库。GNU lightning 在运行时生成汇编代码，速度极快，
非常适合 Just-In-Time 编译器。它向客户端暴露一套受 MIPS 和 SPARC 启发、
与目标 CPU 无关的标准 RISC 指令集，从而抽象掉目标架构差异。

- 官网: https://www.gnu.org/software/lightning/
- 上游源码: https://ftp.gnu.org/gnu/lightning/lightning-2.2.3.tar.gz
- 许可证: LGPL-3.0-or-later

## OHOS 适配

- 构建系统：Autotools（`configure && make`）。
- 平台：支持 aarch64（HarmonyOS PC 目标架构）。
- 可选 disassembler 依赖 binutils（libbfd/libopcodes/libiberty/zlib），
  OHOS 未提供，故显式 `--disable-disassembler` 只构建核心 JIT 库。
- 上游 `make check`（automake TESTS）已在 build() 中集成；aarch64 下运行
  `base_TESTS` + 12 个 C 测试程序，共 79 个用例,汇总写入 `check/test-suite.log`。
- 适配补丁：config.guess / config.sub 增加 HarmonyOS(aarch64-linux-ohos) 识别，
  configure 的 umask 077→022 规避 HMDFS 临时目录权限限制。

## 依赖

- 无第三方构建依赖。

## 参考

- https://git.savannah.nongnu.org/cgit/lightning.git/
