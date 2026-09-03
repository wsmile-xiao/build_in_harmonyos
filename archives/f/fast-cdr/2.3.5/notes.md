# fast-cdr 2.3.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

源码为 CMake 工程（init-build 按 URL 猜测 autotools 有误，配方已在 conan-init 后重写为 CMake 驱动）：

```bash
# 官方 v2.3.5 标签源码 tarball（sha256 已校验）
# URL: https://github.com/eProsima/Fast-CDR/archive/refs/tags/v2.3.5.tar.gz
# sha256: e0af6cde06c4a43d90fa905c6d15721435520a26f0ba168ed13dfda45d164001
python3 scripts/ohc-run.py init-build fast-cdr 2.3.5 --url=<官方URL>
python3 scripts/ohc-run.py conan-init fast-cdr 2.3.5   # 重写 conanfile.py 为 CMakeToolchain
python3 scripts/ohc-run.py conan-verify fast-cdr 2.3.5 # G0-G4 + L2/L4/L5 全通过
python3 scripts/ohc-run.py finish fast-cdr 2.3.5 built
```

CMake 关键配置（conanfile.py generate()）：
- `CMAKE_SYSTEM_NAME=Linux`（OHOS，对应 E092）
- `BUILD_SHARED_LIBS=OFF`（静态库）
- `BUILD_TESTING=ON`（R02 启用上游测试：gtest/1.17.0 依赖 + `-D` 传入 + `GTest_DIR` 官方 config）/ `BUILD_DOCUMENTATION=OFF`（doxygen 不可用网络）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build/conan-init 生成 autotools 模板 | URL 猜测构建系统误判为 autotools | 重写 conanfile.py 为 CMake 驱动（CMakeToolchain/cmake_layout） |
| 2 | test_package 编译错误 `no member named 'DDS_CDR' in 'eprosima::fastcdr::Cdr'` | CdrVersion 枚举定义于 CdrEncoding.hpp 命名空间作用域，非 Cdr 类成员 | 改用 `eprosima::fastcdr::CdrVersion::DDS_CDR`（知识草稿 DRAFT-fast-cdr-2.3.5-cdrversion-enum-scope） |
| 3 | W3 本地 CI 的 junk_check 全仓扫描拦截 | 分支无 commit 时回退 full 模式扫描全仓，误拦 main 上其他库历史遗留状态文件 | 属无关历史基线：以 prdiff 模式（JUNK_PR_DIFF 仅含本库文件）隔离复验通过，基线文件零改动（审计见 task-audits） |
| 4 | R02 上游测试启用：`BUILD_TESTING=ON` 未生效（"Tests not compiled by default"） | CMakeLists.txt 顶部 `if(NOT BUILD_TESTING)` 在 project() 加载 toolchain 前求值并 FORCE 设 OFF，`tc.variables` 写入 toolchain 的 `set(CACHE)` 不覆盖 | 经 `cmake.configure(variables={"BUILD_TESTING": "ON"})` 以 -D 传入命令行，在 project() 前即见 ON |
| 5 | R02 上游测试链接 `GTest::gtest_main` target 缺失 | gtest 1.17.0 配方 package_info 只声明单个 gtest::gtest；CMakeDeps 生成的 gtest-config.cmake 无 GTest::gtest_main | `GTest_DIR` 指向 gtest 包内官方 GTestConfig.cmake（含 GTest::gtest/gtest_main/gmock/gmock_main 完整 targets，指向包内 libgtest*.a） |

## 源码修改

无（Fast-CDR 2.3.5 原生支持 Linux/OHOS 平台，配方零补丁，patches/ 为空）。

## 依赖版本

- 无外部 Conan 依赖（库为自包含 CMake 工程，仅需标准 C++ 工具链）
- toolchain: clang 15.0.4, cmake 4.1.2, ninja/make

## 验证结果

```bash
# conan-verify（G0-G4 + L2/L4/L5）
✅ G0 预构建评估 / G1 配方完整性 / G2 conan create / G3 系统同名库隔离 / G4 产物完整性
✅ L1 test_package: ctest 100% (1/1) — FastBuffer+Cdr DDS_CDR 序列化/反序列化往返
✅ L1e 破坏性反向验证: 移除 lib/include 后重建失败，确认测试真实依赖包产物
# W3 本地 CI 模拟（prdiff 模式，CI 同源）
✅ 100% (1/1) — L0/L1/L4/L5 全通过
# R02 上游测试（BUILD_TESTING=ON, gtest/1.17.0）
✅ 上游 GTest 可执行入口 4 个构建并运行: UnitTests / FixedSizeStringTests /
   ArrayAsSTDVectorTests / xcdr_tests + CTest 模块测试 4 个 (cmake.force_standard.*)
✅ ctest 全量: 100% tests passed, 0 tests failed out of 2107 (20.02s, exit 0)
✅ 日志: /storage/Users/currentUser/tmp/fast-cdr-r02-upstream-ctest.log
   SHA-256: 1a1f8dbeb60c114bed274563aa13cc783fcb286335329e8c415aa6a6f2e1375a
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 驱动配方（含 OHOS 平台映射、静态库、测试/文档开关） |
| conandata.yml | 官方 v2.3.5 源码 URL + sha256 |
| test_package/ | 消费者测试（test_package.cpp: FastBuffer+Cdr 往返 + ctest） |
| manifest.yaml | 版本元数据 + 知识沉淀 |
| reports/test-report.md | 功能测试报告 |
| knowledge/drafts/DRAFT-fast-cdr-2.3.5-cdrversion-enum-scope.{kv,md} | 路径 B 知识草稿对 |

## 注意事项

- 静态库产物 `libfastcdr.a`（非系统同名库，无 R26 冲突）；cmake 包名 `fastcdr`，target `fastcdr::fastcdr`
- 上游 GTest 测试套件（test/cdr、test/xcdr）未编译（BUILD_TESTING=OFF），由 test_package 消费者测试覆盖序列化核心路径
- 路径 B（知识库扩展）：CdrVersion 枚举作用域知识可跨库复用（FastDDS 等 fastcdr 消费者）
---

**编译结束**: 2026-09-03 11:52
**最终状态**: built
