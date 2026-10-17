# rocm-cmake 0.4.0 鸿蒙适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-06
- 编译器: clang 15.0.4 / clang++ 15.0.4
- CMake: 4.1.2
- Git: 2.45.2
- 平台: HarmonyOS PC (aarch64)，制品 `os=OHOS`
- 状态: built（本地 conan create 复验通过前不得写 published）

## 编译步骤

1. 获取源码：conandata.yml 指向官方源
   `https://github.com/ROCm/rocm-cmake/archive/refs/tags/rocm-4.2.0.tar.gz`
   （sha256 `299e190e…85c3b`），该 tag 根 CMakeLists 为
   `rocm_setup_version(VERSION 0.4)`，即 AMD 官方发布的 rocm-cmake 0.4.0。
2. 生成工具链（`generate()`）：`CMakeToolchain` 注入
   `-DCMAKE_POLICY_VERSION_MINIMUM=3.10`（CMake 4.x 策略下限）。
3. 构建（`build()`）：
   - 在 `Environment` 中定义 `CMAKE_POLICY_VERSION_MINIMUM=3.10` 与
     `GIT_AUTHOR_*`/`GIT_COMMITTER_*`，再执行 `cmake.configure()` /
     `cmake.build()`；
   - **层 1 上游测试**（末尾，TEST_QUALITY_SPEC §3.1）：
     `cmake.ctest(cli_args=["--output-on-failure", "-E",
     "'pass-simple-soversion|pass-simple-soversion-env|pass-version-norepo|pass-version-parent'"])`
     —— test/test.cmake 驱动的 19 个真实 configure/build/install 用例。
     ⚠️ **`-E` 的正则必须带字面单引号**：Conan 的 `cmake.ctest()` 把 cli_args
     用空格 join 成**单个 shell 字符串**交 sh 执行（无 argv 数组），不加引号时
     `|` 被 shell 当成管道符，ctest 只收到第一个排除项、其余正则片段被当命令
     执行（实测 exit 127）。且**重复 -E 不累加**（实测 `-E A -E B` 仍为 18 个
     用例）；单条带引号 `-E 'A|B|C|D'` 恰好排除 4 个 → 剩 15 个。
4. 打包（`package()`）：`cmake.install()`，并兜底从源码 `share/rocm/` 复制
   全部 `.cmake` 模块到 `share/rocm/cmake/`。
5. 制品核对：包内为 `share/rocm/cmake/*.cmake`（ROCMConfig / ROCMSetupVersion
   / ROCMInstallTargets / ROCMCreatePackage / ROCMPackageConfigHelpers /
   ROCMInstallSymlinks 等），无 lib/、无 bin/ → `package_type=build-scripts`，
   依 R38 **不写 commands.json**。

复现命令（本地实跑：`conan create` 退出码 0；层 1 上游套件 15/15 通过、4 例平台受限
显式豁免；层 2 `test_package` 10/10 断言通过；命令须使用真实 profile 路径）：
```bash
conan create . -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 -pr:b=<同上>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `pass-simple-soversion` / `pass-simple-soversion-env` 失败（断言 `libsimple.so.1` 缺失） | OHOS 不生成 `.so` 版本化符号链接；普通 CMake SOVERSION 工程实测同样不产版本化软链 | 平台能力差异，**不改上游测试**；测试路径 ctest `-E` 显式排除并在 MANIFEST.yml/本笔记逐条声明豁免（先例 rocm-cmake 0.12.0 同因豁免） |
| 2 | `pass-version-norepo` / `pass-version-parent` 失败（`PROJECT_VERSION_TWEAK` 期望值 0 与空值不等 / 宏参数缺失报错） | 上游版本测试框架依赖 git 元数据：非 git 树内 `git describe` 失败；且 `ROCMSetupVersion` 用 `--match [0-9]*`、测试框架用 `--always`，取值口径不一致 | 配方已注入 `GIT_AUTHOR_*`/`GIT_COMMITTER_*` 身份；但 tarball 非 git 树从根本上无 tag → 用例假设不成立，ctest `-E` 显式排除并逐条声明 |
| 3 | CMake 4.1.2 对 `cmake_minimum_required(VERSION 3.5/3.6)` 在 `-Werror=dev` 下报 Deprecation Error | CMake 4.x 移除对 `<3.5` 的兼容策略；上游测试子工程声明 3.5/3.6 | 设 `CMAKE_POLICY_VERSION_MINIMUM=3.10`。因 `test/test.cmake` 会再次 `configure` 子工程，须**双通道**下发：`tc.cache_variables`（主工程命令行 `-D`）+ `Environment` 环境变量（被嵌套 configure 继承） |
| 4 | git 在非 git 树内操作报错/身份缺失 | 解压的 tarball 无 `.git`，且构建机无 git 身份 | 配方 `build()` 经 `Environment` 注入 `GIT_AUTHOR_NAME/EMAIL`、`GIT_COMMITTER_NAME/EMAIL`（禁止裸用 `${CC}` 等 shell 变量，满足 R33） |
| 5 | `conan create` 时 build() 报 `sh: pass-simple-soversion-env: not found` / `Error 127` | Conan 的 `cmake.ctest()` 把 `cli_args` 用空格 join 成**单个 shell 字符串**交 sh 执行（无 argv 数组）；`-E` 正则未加引号 → `|` 被 shell 当管道符，ctest 只收到第一个排除项，其余正则片段被当命令执行 | 给整段正则加**字面单引号**：`"-E", "'%s'" % _EXCLUDED_CTEST_CASES`。实测对照：重复 `-E` 不累加（`-E A -E B` 仍 18 个）；单条带引号 `-E 'A|B|C|D'` → 15 个（正确） |
| 6 | 层 2 `conan create` 在库目标 TU 编译失败，报 `error: "ROCM_CONSUMER_VERSION must be defined…"` + `error: "ROCM_CONSUMER_PATCH must be defined…"`（`2 errors generated`） | `test_package.cpp` 顶部的两个 `#ifndef … #error` 守卫写在 `#ifdef ROCM_CONSUMER_LIBRARY_ONLY` **之前**，对两个 TU 都生效；而这两个宏只在 `test_package/CMakeLists.txt` 里用 `target_compile_definitions(test_package PRIVATE …)` 定义给**可执行文件**目标，库目标 `rocm_consumer_core` 只带 `ROCM_CONSUMER_LIBRARY_ONLY`，没有那两个宏 → 库 TU 必然 `#error` | 把两个 `#ifndef … #error` 用 `#ifndef ROCM_CONSUMER_LIBRARY_ONLY … #endif` 包裹，作用域限定到可执行文件分支；**保留守卫本身**（有价值的自检），未删断言、未改为从环境读取 |
| 7 | 层 2 install 产出的两条硬断言从未执行（“未验证就宣称已验证”） | `test_package/conanfile.py::build()` 只调 `cmake.configure()` + `cmake.build()`，**从不调 `cmake.install()`**；而 `test_package/CMakeLists.txt` 末尾两条真实产出断言写在 `install(CODE "…")` 里（检查 `librocm_consumer_core.a` 与 `lib/cmake/test_package/test_package-config.cmake` 是否真被 `rocm_install_targets` / `rocm_export_targets` 安装），install 不跑 → 断言永不执行 | 在 `build()` 的 `cmake.build()` 之后、仍在同一 `with env.vars(self).apply():` 块内调用 `cmake.install()`（主配方 `package()` 里已有的 `cmake.install()` 不动） |

## 源码修改

无。未打任何补丁（`patches_applied: []`），未修改上游测试文件。

## 依赖版本

无第三方依赖（`build.dependencies: []`）。

## 验证结果

> 全部结论均来自本地实跑（`conan create` 退出码 0、`conan-verify` G0–G4 全 PASS、
> W3 本地 CI 模拟通过），无待回填项。

```bash
# 层 1：上游官方测试（build() 末尾，ctest -E 显式排除 4 个平台受限用例；
#        正则须带字面单引号，见上表 #5）
ctest --parallel 20 --output-on-failure -E 'pass-simple-soversion|pass-simple-soversion-env|pass-version-norepo|pass-version-parent'
# 实测输出：100% tests passed, 0 tests failed out of 15
# 即：上游 19 用例中 15 例实际执行并全部通过（15/15 = 100%），
#     4 例平台受限显式豁免（见上表 #1 #2，逐条根因已声明）
# 层 2：test_package 消费者端到端（find_package(ROCM) + 宏真实产出 + install 断言 + 运行期断言）
# 实测输出：OK: rocm-cmake 0.4.0 consumer test passed (ROCM_VERSION=0.4.0, PATCH=0, checksum=40)
# 退出码 0 —— configure 期 4 项断言 + 运行期 4 项断言全部通过
```

- 上游测试：**实际执行 15 例，通过 15 例（15/15 = 100%）；上游共 19 例，
  4 例平台受限（2 例 SOVERSION 无版本化软链 + 2 例 git 元数据假设）显式豁免**，
  逐条根因见上表 #1 #2。
- test_package：**8 项断言全部通过**（configure 期 4 项 + 运行期 4 项，退出码 0）。
  执行 `find_package(ROCM REQUIRED)`、`rocm_setup_version` 版本断言 0.4.0、
  `rocm_get_patch_version` 读取 `ROCM_LIBPATCH_VERSION`、
  `rocm_install_targets` + `rocm_export_targets` 真实产出库与 CMake config，
  运行期二进制二次校验版本并返回 0。
- 配方验证：`conan-verify rocm-cmake 0.4.0` → **G0/G1/G2/G3/G4 全 PASS**，
  报告 `reports/conan-verify-report.md`。
- 本地 CI 模拟：`ci/conan/setup.sh` + `ci/conan/build_and_test.sh archives/r/rocm-cmake/0.4.0`
  → **L0/L1 pass（L2 skip 无 bin/、L4 pass、L5 warn 无产物）**，
  `Build Summary: Total 1 / Success 1 / Failed 0 / Pass rate 100.0%`，
  日志 `reports/w3-local-ci.log`。
- 过程中由真实构建暴露并已修复的自身缺陷：#5（`-E` 正则未加引号 → exit 127）、
  #6（宏守卫作用域 → 库 TU 编译失败）、#7（`build()` 未调 `cmake.install()` →
  install 产出断言未执行）；修复后以上三层验证全绿。

## 注意事项

- **不静默跳过**：4 个受限用例通过 ctest `-E` 显式排除，任何时候都不得删除
  测试调用或修改上游测试文件；豁免在 `test_package/MANIFEST.yml` 与本文逐条声明。
- **两类环境修复经 `Environment` 传递**（R33）：`CMAKE_POLICY_VERSION_MINIMUM`
  与 `GIT_*` 身份均不裸用 shell 变量。
- 本包为 build-scripts，无运行期产物，故无 L2 `--version` 冒烟对象；依 R38 不写
  `commands.json`。
- `cmake.test()` 走 `cmake --build --target test`，无法向 ctest 透传 `-E`；本配方
  改用 CMake helper 的 `cmake.ctest()`（同一 ctest 驱动）以便显式排除受限用例。
---

**编译结束**: 2026-10-06 21:48
**最终状态**: built
