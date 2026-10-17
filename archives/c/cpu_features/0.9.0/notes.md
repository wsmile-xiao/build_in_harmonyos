# cpu_features 0.9.0 适配笔记

## 编译环境
- 构建系统: cmake（`project(CpuFeatures VERSION 0.9.0 LANGUAGES C)`）
- 编译日期: 2026-09-06
- 编译器: clang/clang++ 15.0.4（OHOS aarch64，libc++）
- 状态: built
- 平台: HarmonyOS PC（OHOS 6.0, armv8/aarch64）

## 编译步骤

```bash
conan create . --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

- `source()`: 下载官方 GitHub tag v0.9.0 tarball（gh-proxy.com 镜像 fallback），SHA-256 `bdb3484de8297c49b59955c3b22dba834401bc2df984ef5cfc17acbe69c5018e`
- `build()`: cmake configure（`BUILD_TESTING=ON`，外部 gtest）→ 构建库 + list_cpu_features + 4 个测试可执行 → 直接运行并解析 gtest 输出，生成 `HMBS_UPSTREAM_TEST_RESULT`
- `package()`: `cmake.install()`（头文件安装到 include/cpu_features/）+ LICENSE
- `test_package/`: 消费者测试 test.c（GetAarch64Info/GetAarch64FeaturesEnumName 真实 API）+ OHOS 专项 test_ohos.c（库结果与 /proc/cpuinfo 交叉核对）

## 上游测试用例审计（双口径台账）

| 测试程序 | 源码声明 | 说明 |
|----------|---------|------|
| bit_utils_test | 2 | 平台无关 |
| string_view_test | 17 | 平台无关 |
| stack_line_reader_test | 4 | 平台无关 |
| cpuinfo_aarch64_test | 6 | Linux 分支 4；macOS/Windows 分支各 1 互斥 |
| cpuinfo_arm_test | 11 | PROCESSOR_IS_ARM 互斥（不实例化） |
| cpuinfo_x86_test | 69 | PROCESSOR_IS_X86 互斥（不实例化） |
| cpuinfo_mips_test | 7 | 互斥 |
| cpuinfo_ppc_test | 5 | 互斥 |
| cpuinfo_s390x_test | 4 | 互斥 |
| cpuinfo_riscv_test | 5 | 互斥 |
| cpuinfo_loongarch_test | 2 | 互斥 |
| **合计** | **132** | 本配置实例化 27，执行通过 27 |

- `source_declared_total=132`（9 个测试源文件所有 TEST/TEST_F）
- `configured_executable_total=27`（OHOS/armv8 实例化：2+17+4+4）
- `executed_passed_total=27`（4 个可执行全部 PASSED）
- 未实例化 105 = 平台互斥分支（x86/arm/mips/ppc/s390x/riscv/loongarch 套件 + aarch64 的 macOS/Windows 分支）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 时 googletest 下载失败 | 上游在 configure 期 `git clone https://github.com/google/googletest.git`，OHOS CI 无法访问 GitHub | patches/0001：改为 `find_package(GTest CONFIG REQUIRED)` + 将裸 `gtest`/`gmock_main` target 映射到 Conan gtest 包的 `GTest::gtest`/`GTest::gmock_main`；conanfile `test_requires("gtest/1.17.0")` |
| 2 | test_package 编译 `cpu_features_macros.h not found` | 上游 install 将 PUBLIC_HEADER 装到 `include/cpu_features/` 子目录 | test_package 使用 `cpu_features/` 前缀 include（`cpu_features/cpuinfo_aarch64.h`），与官方消费者用法一致 |
| 3 | aarch64 头无 GetAarch64CacheInfo | 缓存信息 API 仅 x86 提供 | test.c 移除该调用，改用 GetAarch64FeaturesEnumName 等公共 API |
| 4 | W3 junk_check full 模式命中其他库历史 junk | 本地未 commit 时 `git diff origin/main...HEAD` 为空 → fallback full 模式扫全仓，命中 main 上已跟踪的其他库 `.build-closed`/`.staging-verified` 等 9 个基线文件 | 基线隔离复验：记录路径 + 隔离前 SHA-256 → prdiff 模式（仅当前库 10 文件）复跑 0 命中 → 恢复并核对 SHA-256 一致 |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`：测试部分改用外部 GoogleTest（find_package + 裸 target 映射）

## 依赖版本

- gtest/1.17.0（test_requires，OHOS armv8 预编译已发布）
- gmock/1.17.0（gtest 传递依赖）

## 验证结果

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64   # EXIT=0
# 上游测试: 27/27 PASSED (bit_utils 2 + string_view 17 + stack_line_reader 4 + cpuinfo_aarch64 4)
# test_package: 2/2 PASSED (test_cpu_features + test_cpu_features_ohos)
```

## 注意事项

- conandata.yml 主 URL 为官方 GitHub，gh-proxy.com 镜像作 fallback（仓库惯例，absl/ACE 同款）
- 全量通过率口径：27/132（20.5%）；当前配置可执行集合：27/27（100%）
---

**编译结束**: 2026-09-06 23:13
**最终状态**: built
