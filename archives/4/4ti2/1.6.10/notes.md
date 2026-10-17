# 4ti2 1.6.10 Adaptation Notes

## Build System
Autotools (configure + make)

## Dependencies
- glpk/5.0 (from conan)
- gmp/6.3.0 (from conan)

## OHOS Adaptation Issues

### 1. config.guess Cannot Recognize OHOS
- Fix: Pass `--build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl`

### 2. config.status mktemp Permission Issue
- Issue: `mktemp -d` with `umask 077` creates dirs with setgid but no group-execute on OHOS/SELinux
- Fix: Patch configure script to use `mkdir` instead of `mktemp -d`

### 3. /bin/bash Shebang
- Fix: Patch shebangs in test/*.in templates BEFORE configure (configure
  generates the runnable scripts from them), so generated scripts use
  `/data/service/hnp/bin/bash`

### 4. CONFIG_SHELL
- Fix: Set `CONFIG_SHELL=/data/service/hnp/bin/bash`

## Build Output
- Executables: 4ti2int32, 4ti2int64, circuits, genmodel, gensymm, groebner, graver, hilbert, markov, minimize, normalform, output, ppi, qsolve, rays, walk, zbasis, zsolve
- Libraries: lib4ti2util.a, lib4ti2common.a, lib4ti2int32.a, lib4ti2int64.a, libzsolve.a
- 注：lib4ti2gmp.a / 4ti2gmp 可执行文件未构建——conan gmp/6.3.0 仅含 C API（无
  gmpxx.h），configure 检测不到 GMP C++ 绑定（HAVE_GMP_WITH_CXX 未定义）。

## 上游测试清点（R51 三步法）

上游 4ti2 1.6.10 注册测试共 189 项：
- 185 个 CLI .chk 用例（circuits 6 / genmodel 4 / gensymm 1 / graver 7 /
  groebner 24 / hilbert 11 / markov 52 / minimize 7 / normalform 2 / output 3 /
  ppi 3 / qsolve 19 / rays 14 / walk 4 / zbasis 10 / zsolve 18），
  由 test/check.template（configure 从 check.template.in 生成）按 flavor
  展开为 235 次工具调用
- 4 个 API 测试：qsolve/api 的 qsolve_main、rays_main、circuits_main
  （TESTS 注册）+ zsolve/api 的 test_zsolve_api（TESTS 注册）

## 上游测试实测（OHOS 真机，2026-09-17）

在 OHOS aarch64 真机上对 W3 conan create 构建树执行完整 `make check -k`：

| 类别 | 实测 | 结果 |
|------|------|------|
| CLI check.template（235 次调用） | 231 passed / 4 FAILED | 98.3% 通过 |
| walk -p arb（4 例：344/cuww1/grin/prob20） | 4 FAILED | 根因见下 |
| qsolve API: qsolve_main / rays_main / circuits_main | 3/3 PASS（exit 0） | 直接执行 |
| zsolve API: test_zsolve_api | 1/1 PASS（automake 汇总） | make check |

未通过项的具体技术原因（同一根因，非 OHOS 平台问题、非 4ti2 代码缺陷）：
- conan gmp/6.3.0 制品仅含 C API 头文件（include/ 只有 gmp.h，无 gmpxx.h）
- 4ti2 任意精度后端需要 GMP C++ 绑定：configure 未检测到 → lib4ti2gmp 与
  4ti2gmp 可执行文件不构建
- `walk -p arb` 运行时报 `Error: Unable to find 4ti2 executable '4ti2gmp'`
  → 4 例 walk arb flavor 失败
- test/qsolve/api/test_input_conversion_gmp.cpp 编译需 gmpxx.h → 2 个
  input_conversion 测试无法构建（automake check-am 在该目录报 Error 2，
  qsolve_main 等 3 个 TESTS 已构建但 check-TESTS 被阻断，故手动直接执行验证）
- 待 gmp 制品提供 C++ 绑定（gmpxx.h + libgmpxx）后，以上 6 项可转绿；
  int32/int64 双精度路径与全部其余功能在本平台完整验证通过

## test_package 实测
- test.c mirrors upstream test/qsolve/api/qsolve_main.cpp (qsolve C API,
  INT_64): builds mat/rel/sign matrices, computes, verifies the 4x3 qhom
  matrix (rows/cols + 12 entries, 18 assertions); compiled with clang
  against installed headers, linked with clang++ against
  lib4ti2int64/common/util + glpk/gmp (static libs).
- test() also runs the packaged gensymm CLI binary (1 assertion).
- Total assertion_count: 21（口径：test.c 全部 20 个 return 1 失败分支 +
  gensymm 执行 1；8 前置检查 + 2 维度 + 12 元素比较 = 20）。

## R6 说明（build() 内联修改未走 patches/ 管线的原因）
- configure 的 mktemp→mkdir 修复与测试脚本 shebang 修复均在 build() 内联
  完成：configure/check.template.in 等为 tarball 内生成文件，上游模板文本
  变动时精确匹配替换 + 未命中显式告警（self.output.warn）比静态 patch 更
  易维护；shebang 依赖设备路径 /data/service/hnp/bin/bash，写入补丁会把
  本机路径固化进 patches/（R8 补丁中平台相关内容从严）。

## Test Results 汇总
- 上游 make check（真机）：231/235 CLI 调用通过 + API 4/4 通过（详见上表）
- conan create G2: PASSED
- test_package（qsolve C API + gensymm CLI）: PASSED，assertion_count 21
  （详见「test_package 实测」节）
---

**编译结束**: 2026-09-17 12:28
**最终状态**: built
