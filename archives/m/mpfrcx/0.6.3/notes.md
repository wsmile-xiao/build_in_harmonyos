# mpfrcx 0.6.3 适配笔记

## 编译环境

- 构建系统: autotools（configure + make）
- 目标平台: OpenHarmony PC (aarch64, musl/libc++)
- 工具链: clang 15（OHOS SDK）
- 依赖: gmp/6.3.0、mpfr/4.2.2、mpc/1.3.1（均为本仓库 Conan 包）

## 源码核实

- 官方源: https://www.multiprecision.org/downloads/mpfrcx-0.6.3.tar.gz（作者 Andreas Enge 官网，gforge.inria.fr 已关闭返回 403）
- SHA256: `9da9b3614c0a3e00e6ed2b82fc935d1c838d97074dc59cb388f8fafbe3db8594`
- License: LGPL-3.0-or-later（源码内 COPYING.LESSER / COPYING.GPL）
- 构建系统: autotools；库目标 `src/libmpfrcx.la`（-version-info 3:3:2），头文件 `src/mpfrcx.h` 安装到 include
- 依赖闭包: gmp（gmp.h）、mpfr（mpfr.h）、mpc（mpc.h），configure.ac 使用 `--with-gmp=DIR` / `--with-mpfr=DIR` / `--with-mpc=DIR`
- 上游正式测试: `tests/Makefile.am` 的 `TESTS = $(check_PROGRAMS)`，共 17 个测试程序（tc_neg/tc_add/tc_sub/tc_mul/tc_swap/tc_derive/tc_tree、tf_* 对应实数版、tc_eval/tf_eval、tc_tower/tf_tower、tget_version）

## 应用的补丁

1. **0001-build-aux-config.guess.patch** — 添加 `*:HarmonyOS:*:*` 分支，输出 `<machine>-unknown-linux-ohos`
2. **0002-build-aux-config.sub.patch** — kernel-os 白名单接受 `linux-ohos*`
3. **0003-configure-tmpdir.patch** — configure 建 tmp 目录改为 `${TMPDIR:-.}` 且 umask 022，规避 OHOS 用户存储对 077 目录的写入限制

与 mpc/1.3.1 的差异：mpfrcx 的 configure.ac `--with-gmp` 系列参数只接受一个 DIR（同时加 -I 和 -L），没有 `-include`/`-lib` 拆分参数，配方必须传 `--with-gmp=<prefix>` 而非 `--with-gmp-include=... --with-gmp-lib=...`。

## 构建方式

沿用 mpc/1.3.1 的 OHOS 配方模式：

1. `_dependency_prefix()` 在 OHOS 上把每个依赖包的 include/lib 复制到 `generators_folder/ohos-deps/<dep>`（剔除 `.la`），避免 libtool 追随依赖包 `.la` 中的 `//lib/...` 死链
2. `TMPDIR` 指到 `~/tmp/mpfrcx-<pid>` 并 chmod 755，配合 0003 补丁
3. OHOS 上显式传 `AR/LD/RANLIB/NM/OBJDUMP/STRIP` 为 SDK 的 llvm 工具
4. `build()` 内 `make check -j1` 实际运行上游 17 个测试（交叉构建在 OHOS self-hosted 机器上直接执行）
5. `package()` 用 `autotools.install()`，删除 `.la`，复制 COPYING 到 licenses/

## 上游测试结果

`make check -j1` 实测：**19/19 PASS**

```
PASS: tc_neg  PASS: tc_add   PASS: tc_sub   PASS: tc_mul
PASS: tc_swap PASS: tc_derive PASS: tc_tree
PASS: tf_neg  PASS: tf_add   PASS: tf_sub   PASS: tf_mul
PASS: tf_swap PASS: tf_derive PASS: tf_tree
PASS: tc_eval PASS: tf_eval  PASS: tc_tower PASS: tf_tower
PASS: tget_version
============================================================================
Testsuite summary for mpfrcx 0.6.3
# TOTAL: 19  # PASS: 19  # SKIP: 0  # XFAIL: 0  # FAIL: 0  # XPASS: 0
```

在 OHOS self-hosted 机器（本机即 HarmonyOS PC aarch64）上原生执行，非交叉跳过、非模拟结果。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 上游脚本无该分支 | 补丁 0001 添加 HarmonyOS 分支 |
| 2 | config.sub 拒绝 linux-ohos | kernel-os 白名单缺失 | 补丁 0002 添加 linux-ohos* |
| 3 | configure mktemp 目录权限不足 | umask 077 + 相对路径 | 补丁 0003 改 TMPDIR + umask 022 |
| 4 | `--with-gmp-include` 参数不被接受 | mpfrcx configure.ac 只有 `--with-gmp=DIR` 单参数形式 | 配方传单一前缀形式 |
| 5 | 2021 版 config.guess 设 GUESS 后未退出，落入 dummy.c 兜底路径报 "unable to guess system type" | 该年代脚本无统一 `GUESS=...; echo $GUESS` 尾部（grep -c 'GUESS=' = 0），主 case 各分支直接 `echo; exit` | HarmonyOS 分支按同期惯例直接 `echo "${MACHINE}-unknown-linux-ohos"; exit`（见 DRAFT-config-guess-era-echo-exit） |
| 6 | config.guess 自身 `set_cc_for_build` 的 mktemp（umask 077）在 HMDFS 上创建 700 目录导致 dummy.c 编译 Permission denied | 与 configure 同根因（E011：HMDFS 对 umask 077 目录的属主写入限制） | 补丁 0001 第一 hunk 将 set_cc_for_build 三处 umask 077 → 022 |

## 消费者测试与鸿蒙特有测试

- test_package/test.c：从最终包链接，覆盖复数高精度多项式加、减、乘、求值、实部提取、精度控制（set_prec 语义：重置为零多项式）、边界输入（零多项式求值/乘法/比较、常多项式求值、拷贝相等），共 24 组断言，实测全过
- test_package/ohos_special_test.cpp：验证包产物 ELF64/LE/AArch64（自解析 ELF 头）、静态库 ar 魔数、宿主绝对路径(/storage,/home,/tmp)泄漏扫描（memmem 全文件扫描）、__OHOS__ 宏，并在设备上真实执行 256-bit 复数多项式求值与实部多项式运算，共 8 组断言，实测全过

## Scoped CI 实测（build_and_test.sh）

`CI_PACKAGES=archives/m/mpfrcx/0.6.3`，结果 100% pass（1/1）：

- G0/G0e：知识库完整性 + 根目录白名单 pass（540 entries）
- KC：知识库质量门禁 pass（KC1–KC5 全过）
- JC：垃圾文件检测 pass（pr.diff 模式，14 个文件均在 mpfrcx 目录）
- L0：质量门禁 pass（依赖在 registry、无版本冲突、目录结构合法）
- L1：pass — make check 19/19（L1a/L1b/L1c）+ test_package 24 断言 + ohos_special_test 8 断言
- L1e：pass — 破坏性负测试（移走 lib/、include/ 后 test_package 确实失败，证明测试真实依赖本包）
- L2：skip（库包无 bin/）
- L4：warn — 补丁 0001 命中关键词扫描，实为将 config.guess 的 mktemp umask 077→022（修复 HMDFS 权限问题），非引入危险代码，良性
- L5：pass（lib/ 有产物）
- conan create 全流程通过，ci-metadata.json 生成（本地运行，runner=manual）
