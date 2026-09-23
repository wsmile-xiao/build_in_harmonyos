# libdecaf 1.0.2 — OHOS 适配笔记

> 任务：feat/libdecaf-1.0.2 积分赛。设备：aarch64 HarmonyOS（clang 交叉）。
> 本地验证：finish 内部 W3（conan create，ohos-aarch64 profile）。

## W0 依赖检查

- 上游无外部库依赖（纯 C，仅 libc + 构建期 python3），requires 为空。
- `w0` 报告：`$TASK/w0.json`。版本占用检查为 blocked：私有 CONAN_HOME 匿名
  访问 ohpcd 远端报 `error:system acceleration policy not enabled`，回退
  `conan install --build=never` 因任务环境缺 build profile 未完成探测
  （技术索引 TECHNICAL_NOTES.md「W0 探针」已知情形；dbf2mysql-1.14a 先例同
  状况不阻断）。目标 `libdecaf/1.0.2` 为全新版本：本任务开始时
  upstream/main 的 archives/ 与 SUMMARY.md 均无 libdecaf 条目（sparse
  worktree 与主检出双向核对），CI L0j 的同版本占用门禁以 CI 侧检查为准。

## 源码来源（R39 论证）

- 上游官方渠道 SourceForge `ed448goldilocks`：files 页仅发布
  1.0.3/1.0.0/0.9.4 的 tarball；1.0.2 只存在于官方 git 仓库 tag
  `v1.0.2`（= da2f2f9b2ab1bce9a2bb77e4f37037ee135fdd72，2022-07-13）。
  SourceForge 的 code-snapshot 与 ci/tarball 均不可用（404/HTML）。
- 本任务采用 Ubuntu/Debian 打包所用的上游 orig tarball（launchpad 托管，
  与 Debian pool 文件 SHA256 相同）：
  `libdecaf_1.0.2.orig.tar.gz`,
  SHA256 `96ce1f59bfc6257748d44dffeb40684c886a0742a8ed10524201e6ad95598552`。
- 一致性验证：设备上 `git clone --branch v1.0.2` 官方 git
  （git.code.sf.net/p/ed448goldilocks/code），`git archive v1.0.2` 解包后
  与 orig tarball 解包 `diff -r` 零差异。orig tarball 为上游 v1.0.2 树的
  忠实打包，非 Debian 修改源（未打 +dfsg，无 debian/ 目录）。

## 构建系统与补丁

CMake（`project(DECAF VERSION 1.0 LANGUAGES C CXX)`），纯 C 库 + 生成的
C/C++ 头；两个 portability 补丁：

1. `0001-cmake-min-version-3.5.patch`：CMake 4.x 已移除
   `cmake_minimum_required(VERSION 3.0)` 兼容（设备 cmake 4.1.2 实测报错
   "Compatibility with CMake < 3.5 has been removed"）。
2. `0002-fix-arm64-arch-detection.patch`：上游
   `if(${CMAKE_SYSTEM_PROCESSOR} MATCHES "arch64")` 展开后 `aarch64` 被
   CMake 当作变量名再次求值→未定义→恒假→所有架构分支失效，回落通用
   arch_32。改为 `if(CMAKE_SYSTEM_PROCESSOR MATCHES ...)`（bare 变量自动
   解引用），配方注入 `-DCMAKE_SYSTEM_PROCESSOR=aarch64` 后正确选择
   arch_ref64。验证：设备原生 aarch64 + 模拟 toolchain（SYSTEM_NAME=Linux,
   SYSTEM_PROCESSOR=aarch64）configure 输出 "Target architecture is 64
   bits general purpose" 且全量构建+测试通过。

配方侧参数：`ENABLE_SHARED/ENABLE_STATIC` 随 shared 选项二选一、
`ENABLE_STRICT=OFF`（上游 -Werror 默认值与新 clang 的
`-Wdeprecated-copy` 冲突，secure_buffer.hxx 的 Block 类被报错，库本体为
C 不受影响，测试与 C++ 消费者受影响）、`CMAKE_SYSTEM_NAME=HarmonyOS` +
`CMAKE_SYSTEM_PROCESSOR=aarch64`（仓库惯例）。

## 上游测试清点与实跑（R51）

清点（上游 test/，`ENABLE_TESTS=ON` 时编译）：

| 测试程序 | CTest 注册 | 说明 |
| --- | --- | --- |
| decaf_tester (test_decaf.cxx) | 是（decaf） | 19 组测试全 PASS（Curve25519/Ed448 算术、Elligator、EC、EdDSA、ECDH、CFRG/Ristretto/Dalek 向量），NTESTS=10000 迭代 |
| bench (bench_decaf.cxx) | 是（bench） | 基准冒烟，通过 |
| ristretto_tester (ristretto.cxx) | 否 | 交互式调试计算器，构建成功；非交互环境仅输出用法后退出（exit 254），不适合自动化 |
| shakesum_tester (shakesum.c) | 否 | 摘要工具；`shake256 < file` 管道模式实测输出摘要、exit 0 |

实跑（设备原生 aarch64，clang，模拟 toolchain，ref64 路径，ENABLE_STRICT=OFF）：

- `ctest --output-on-failure`：**2/2 通过**（decaf 61.33s、bench 0.77s）。
- `decaf_tester`：**19/19 组 [PASS]，"Passed all tests."**
- 原始日志：`$TASK/upstream-evidence/upstream-test-run.log`。

适配后（配方）测试：test_package 消费者测试 test_libdecaf 6 项
（`conan create` 内自动运行），`ENABLE_TESTS` 保持上游默认 OFF，不把上游
测试程序装入包。

## 消费者 API 注意点

- 公共头安装于 `<prefix>/include/decaf/`（decaf.h、decaf/point_448.h 等），
  消费者 include 根是 `include/decaf`（与上游 CMake 接口一致），
  `package_info()` 已显式设置 `includedirs=["include/decaf"]`。
- 错误码：`decaf_error_t`（DECAF_SUCCESS=-1 / DECAF_FAILURE=0）；
  布尔：`decaf_bool_t`（DECAF_TRUE 全 1 / DECAF_FALSE=0）。

## W0b 历史核验

本仓库无 libdecaf 历史归档（archives/ 与知识图谱无条目），无历史 notes
可继承；CI 能力矩阵：C/C++/cmake/python3 均可用，无 Rust/OCaml 依赖。
