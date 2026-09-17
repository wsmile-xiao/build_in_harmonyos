# libgkarrays 2.1.0 adaptation notes

## 上游与源码

- 上游：Gk-arrays（C++ 库，主页 http://crac.gforge.inria.fr/gkarrays/，论文 Philippe et al. BMC Bioinformatics 2011）。
- 原始发布站 gforge.inria.fr 已退役，原始 `libGkArrays-2.1.0.tar.gz` 不可达。本配方使用 Debian/Ubuntu 权威归档的 dfsg 重打包：
  - `https://deb.debian.org/debian/pool/main/libg/libgkarrays/libgkarrays_2.1.0+dfsg.orig.tar.xz`
  - `https://archive.ubuntu.com/ubuntu/pool/universe/libg/libgkarrays/libgkarrays_2.1.0+dfsg.orig.tar.xz`
  - 两者逐字节相同，sha256 `bb73beac...04bb84` 与 Debian `.dsc` 记录一致（`libgkarrays_2.1.0+dfsg-4.dsc`）。
- dfsg 仅剔除自动生成的 autotools 文件（`configure`、`Makefile.in`、`config.guess/sub` 等，见 `debian/copyright` Files-Excluded），源码本身完整。配方在 `build()` 中运行 `autoreconf -fi` 重生成。
- 构建系统：Autotools（`configure.ac` + `src/Makefile.am` + `tests/Makefile.am`）。
- 依赖：`zlib`（`AC_CHECK_LIB([z], [gzread])`）、`pthread`；内嵌 `src/libProgressBar-1.2.0` 默认随构建（`AC_CONFIG_SUBDIRS`），无需外部依赖。
- 许可证：主库 CeCILL-C；`src/basic.h` LGPL-2.1+、`src/sux/*` LGPL-3+、`src/kseq/kseq.h` MIT（见 Debian copyright）。

## 上游测试清点（`tests/Makefile.am`）

- `TESTS = testPairedEnd testVariableFixed testConsistency`，共 3 个 `make check` 用例。
- `check_PROGRAMS` 另含 `variableAndFixedLength`（仅编译，不计入 TESTS）。
- 各二进制为 TAP 风格（`tests/testing.h`），内部断言数：`testPairedEnd` 1（NB_TESTS=1）、`testVariableFixed` 8（`compareVariableFixed.h` 枚举）、`testConsistency` 22（`checkConsistency.h` 枚举）。
- 数据集：`tests/dataset/data1.fa`、`data2.fa`、`variable.fa`，随包发布，离线可用，无需网络、GTest 或 Python。
- 配方在 `build()` 中执行 `autotools.make(target="check")`，并解析 `tests/test-suite.log` 的 `# TOTAL/# PASS/# FAIL/# SKIP` 生成 `HMBS_UPSTREAM_TEST_RESULT`；失败时抛异常中断构建。

## 消费者测试（`test_package/test_package.cpp`，6 断言）

1. `libGkArraysVersion()` 非空。
2. 版本字符串等于 `2.1.0`（`gkArrays.cpp` 返回 `PACKAGE_VERSION`）。
3. `isDiscarded(10,20,4)` 为 true（短于理论长度）。
4. `isDiscarded(30,20,4)` 为 false。
5. `isDiscarded(3,0,4)` 为 true（短于 k）。
6. `SolArray(4,255,SMALL_ARRAY)` 的 set/get/length 往返。
- `test()` 运行二进制成功后输出 `HMBS_TEST_PACKAGE_RESULT`（discovered=6/passedCount=6）。

## HarmonyOS 适配要点

- `generate()` 预置 mktemp wrapper（`exit 1` 迫使 autoconf 用 mkdir fallback），复用 `bash/5.3` 已验证方案；同时 `--build=aarch64-unknown-linux-gnu` 规避老 `config.guess` 识别问题。
- `package()` 删除 `*.la`，并把版本化头文件目录（`include/libGkArrays-2.1.0`）与 `config.h`（`lib/libGkArrays-2.1.0/include/`）扁平化一份到顶层 `include/`，消费者可直接 `#include <gkArrays.h>`；原版本化树保留兼容。
- `cpp_info.libs = ["GkArrays"]`，`system_libs = ["m", "pthread"]`，并声明 `cmake_file_name`/`cmake_target_name`/`pkg_config_name` 供 `CMakeDeps` 使用。
- 首轮未带 `patches/`：Debian 的 `proper_soname`（去 `-release`）与 `fix_pkg-config` 已知，若 CI L5 报告 SONAME/`*.cmake` 问题再补。本轮保持最小改动，待真机证据驱动。

## 已知风险（待真机验证）

- `u_int64_t`/`u_int32_t` 等 BSD 类型在 OHOS libc 是否可用未知；若 `configure` 通过但编译报错，需补可移植补丁。
- `AC_CHECK_LIB([pthread], ...)` 在 OHOS（pthread 合入 libc）是否通过未知；若失败需调整为弱检查或去 `-lpthread`。
- 内嵌 ProgressBar 子目录的 libtool 归档是否与主库 SONAME 门禁冲突，待 CI L5 结论。

## 验证

- 本地未运行 conan（按任务守则由 HMBS 后台在 HarmonyOS aarch64 真机执行 `conan create` 全量验证）。
- 待 HMBS 预检返回后，如实回填 PR 正文的执行数/通过数，并做“证伪一次”（检查参照文件非空、确认 harness 能捕获失败、区分跳过与通过）。
