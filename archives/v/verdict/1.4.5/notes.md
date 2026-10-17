# verdict 1.4.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-18
- 编译器: clang/clang++ (OHOS SDK 26.0.0.18, clang 15.0.4)
- 目标平台: HarmonyOS PC / OpenHarmony aarch64 (os=OHOS, arch=armv8, clang 15, libc++, cppstd 17)
- 状态: built（W3 本地验证通过）

## 上游测试清点（R51 第一步）

```bash
$ ls unittests/
CMakeLists.txt  unittest_main.cpp  verdict.test.cpp

$ grep -c "TEST(" unittests/verdict.test.cpp
67

$ grep -n "add_verdict_unittests" CMakeLists.txt
245:  add_verdict_unittests(unittests unittests_verdict)
```

- 测试框架: GoogleTest（`unittest_main.cpp` → `::testing::InitGoogleTest` + `RUN_ALL_TESTS`）
- CTest 注册数: 1 个入口 `UT-unittests_verdict`（二进制 `unittests_verdict`），内含 67 个 `TEST()` 用例
- 上游测试依赖: GoogleTest（CMake `find_package(GTest REQUIRED)`）

## 编译步骤

```bash
# 1. 配方生成（本仓库工具）
python3 scripts/ohc-run.py init-build verdict 1.4.5 \
  --url=https://github.com/sandialabs/verdict/archive/refs/tags/1.4.5.tar.gz
python3 scripts/ohc-run.py conan-init verdict 1.4.5

# 2. W3 本地验证（OHOS-adapted conan 2.29.1，真机 native）
python3 scripts/ohc-run.py conan-verify verdict 1.4.5 --profile ohos-aarch64-device
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 设备直连 github.com 下载超时 | 网络对 github.com archive 端点不稳定 | conandata 保持官方 URL；本地验证由 conan-verify 自动注入 ghfast 镜像，CI 由 build_and_test.sh 自动加镜像回退 |
| 2 | 初始 conanfile 从 conan 顶层导入 ConanException 失败 | Conan 2.29 中该类位于 conan.errors | `from conan.errors import ConanException` |

## 源码修改

无。上游源码零改动（无 patches/）。GTest 目标通过 CMake 原生 `find_package(GTest)`
（Module 模式）解析到 Conan 提供的 gtest 包，`GTest::GTest` 可用，上游
`unittests/CMakeLists.txt` 无需修改。

## 依赖版本

- gtest/1.17.0.1（test_requires，仅构建期构建并运行上游单测；不进入运行/产物依赖）
- 运行期依赖: 无（libverdict 静态库，仅链接 OHOS libc/libc++/libm）

## 验证结果

```bash
$ conan create archives/v/verdict/1.4.5 -pr:h=ohos-aarch64-device -pr:b=ohos-aarch64-device \
    --build=missing -r=ohpcd --user=ohpcd --channel=stable
...
verdict/1.4.5@ohpcd/stable: HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "gtest",
  "command": "./unittests/unittests_verdict", "discovered": 67, "executed": 67,
  "passed": 67, "failed": 0, "skipped": 0}
...
verdict consumer checks: 10/10 passed
verdict/1.4.5@ohpcd/stable (test package): HMBS_TEST_PACKAGE_RESULT={"executed": true,
  "passed": true, "command": "./test_verdict", "discovered": 10, "passedCount": 10}
```

- 上游用例: 67/67 通过（100%）
- test_package 消费者断言: 10/10 通过
- 产物: lib/libverdict.a + include/verdict.h + include/verdict_config.h

**编译结束**: 2026-09-18
