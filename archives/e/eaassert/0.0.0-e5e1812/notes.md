# eaassert 0.0.0-e5e1812 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-15
- 编译器: clang/clang++ 15.0.4（OHOS SDK sysroot，aarch64-linux-ohos）
- 平台: HarmonyOS PC aarch64（OHOS 6.0）
- 依赖: eabase/0699a15（制品仓已发布）

## 编译步骤

1. `init-build eaassert 0.0.0-e5e1812 --url=https://github.com/electronicarts/EAAssert/archive/e5e1812....tar.gz`
   - 官方 commit e5e181255de2e883dd1f987c78ccc42ac81d3bca（2019-06-13）
   - SHA-256 与官方 GitHub archive 重下载逐字节比对一致：125c3a93863c7e382c616baf053ec00c040c1a5f380a63840b265411c364ab55
2. `lang-preflight` → detected=cpp，通过（R47）
3. 本机构建（CMake）：`cmake .. -DEAASSERT_BUILD_TESTS=ON` + `make -j2`
   - EAThread 测试框架子模块需 OHOS 适配（见下），修复后 EAAssertTest 构建成功、运行 RETURNCODE=0
4. `conan-init` 生成配方 → 改为 CMake 配方（autotools 模板不适用）
5. `conan-verify`（ohos-aarch64 profile，clang 15，CMake 4.1.2）：
   - 需要 5 个 portability 补丁（见下）才能通过干净构建
   - G2 conan create：库本体 + test_package 消费者全部编译链接运行通过（12 项断言语义断言 errors=0）
   - G3/G4/L2/L4/L5 全 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake_minimum_required(VERSION 3.1)` configure 报 "Compatibility with CMake < 3.5 has been removed" | CMake 4.x 移除 <3.5 兼容；conan toolchain 注入的 CMAKE_POLICY_VERSION_MINIMUM 在 cmake_minimum_required 之后才加载无效 | 补丁 0001/0002 提升为 3.5（复用 E103） |
| 2 | `include could not find requested file: CommonCppFlags` | CommonCppFlags 位于 EASTL 测试子模块（tarball 不含子模块内容） | 补丁 0003/0004 `if(EXISTS ...) include() endif()` 守卫 |
| 3 | `target_link_libraries(EAAssert EABase)` 裸目标 + `EABase/eabase.h not found` | 上游假设 EABase 以子模块内嵌，干净 Conan 构建无该目标，eabase include 不传播 | 补丁 0005 `find_package(eabase)` + `eabase::eabase`；配方 `generators="CMakeDeps"` + `requires="eabase/0699a15"` |
| 4 | test_package 消费者 `EABase/eabase.h not found` | eabase（header-only）经 CMakeDeps 生成的 INCLUDE_DIRS 为空 | 配方 package_info：`cpp_info.requires=[eabase::eabase]` + 显式把依赖包 includedirs 绝对路径追加进本包 includedirs |
| 5 | sample: EAThread `pthread_setaffinity_np`/`pthread_setcancelstate` undeclared | OHOS musl libc 无 glibc pthread affinity/cancel 扩展 | 测试框架子模块本地适配：`sched_setaffinity(0,...)` + `!defined(__OHOS__)` 守卫（复用 E211；仅本地测试运行，不进入交付配方） |

## 源码修改

5 个 portability 补丁（仅改上游 CMakeLists.txt，未触及框架只读路径）：

| 补丁 | 修改 |
|------|------|
| 0001-cmake-min-version-3.5.patch | 顶层 CMakeLists.txt cmake_minimum_required 3.1→3.5 |
| 0002-cmake-min-version-3.5-test.patch | test/CMakeLists.txt 同改 |
| 0003-guard-commoncppflags.patch | 顶层 include(CommonCppFlags) 加 EXISTS 守卫 |
| 0004-guard-commoncppflags-test.patch | test/CMakeLists.txt 同改 |
| 0005-eabase-target-link.patch | target_link_libraries(EAAssert EABase) → find_package(eabase)+eabase::eabase |

## 依赖版本

- eabase/0699a15（ohpcd 制品仓已发布，header-only，提供 EABase 头文件）

## 验证结果

```bash
# 上游测试（本地完整子模块恢复构建）
./build-native/test/EAAssertTest  # Test complete - all tests passed. RETURNCODE=0

# 鸿蒙专项消费者测试（仅公开头文件/API/链接目标）
./build-ohos-test/test_ohos_eaassert # PASS (errors=0)

# conan-verify（ohos-aarch64 干净构建）
conan create ... -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# → G2 conan create PASS（库本体 + test_package 消费者运行 errors=0）；G3/G4/L2/L4/L5 PASS
```

双口径：源码声明 2（TestEAAssert.cpp + TestEAAssertC.c，后者上游未实例化）/ 配置可执行 1 / 实际执行通过 1（RETURNCODE=0）；全量 1/2=50%，当前配置可执行集合 1/1=100%（详见 reports/test-report.md）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方，requires eabase，package_info 显式传播依赖 include |
| conandata.yml | 官方源 + SHA-256 + 5 补丁声明 |
| test_package/ | 消费者测试（conanfile.py + CMakeLists.txt + test.cpp + MANIFEST.yml） |
| patches/ | 5 个 portability 补丁 |
| reports/ | conan-verify-report.md / test-report.md / knowledge-candidate-ledger.md |
| knowledge/drafts/DRAFT-EA-headeronly-dependency-chain.kv/.md | 路径 B 知识草稿（EA header-only 依赖链适配） |

## 注意事项

- EAAssert 为纯断言库（library），无 CLI 产物 → 无需 commands.json（R38）
- 知识路径：B（new_draft DRAFT-EA-headeronly-dependency-chain，七轴查重组合/边界/测试迁移三轴新增；E103/E211 复用）
- 状态：built（conan-verify + 本地 W3 通过，未 upload；upload 由 CI 合并后 release 流水线执行）
---

**编译结束**: 2026-09-15 21:58
**最终状态**: built
