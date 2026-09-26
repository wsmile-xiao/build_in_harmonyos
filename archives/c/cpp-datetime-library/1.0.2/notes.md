# cpp-datetime-library 1.0.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

```bash
# 1. 下载官方 tag tarball 并核验 SHA-256
curl -sSL -o src.tar.gz https://github.com/jeremydumais/CPP-DateTime-library/archive/refs/tags/v1.0.2.tar.gz
sha256sum src.tar.gz   # 97ade0d8880fed2454e8c86cbb7fc01542287e1c6b82bc23cb43d621bf4facac

# 2. CMake 配置 + 构建（主库）
cmake <src> -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF
cmake --build . -j2        # 产出 libdatetime.a

# 3. 上游测试（gtest 191 用例，本地构建 googletest 1.14.0 后手动链接运行）
#    datetime_unittest.cpp 117 用例 + timespan_unittest.cpp 74 用例，全部通过
clang++ -std=c++17 -Isrc -I<gtest>/googletest/include \
    test/datetime_unittest/main.cpp \
    test/datetime_unittest/datetime_unittest.cpp \
    test/datetime_unittest/timespan_unittest.cpp \
    libdatetime.a libgtest.a libgtest_main.a -pthread -o datetime_tests
./datetime_tests    # 191/191 PASSED

# 4. Conan 配方：conan-init 生成 autotools 模板后改写为 CMake 配方
#    （上游是 CMake 项目；BUILD_TESTING=OFF 避免构建期联网拉 googletest）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载官方仓库根 URL 得到 HTML | 传入的是仓库页而非 tarball | 改用官方 tag tarball URL `archive/refs/tags/v1.0.2.tar.gz` |
| 2 | conan-init 生成 autotools 模板 | 构建系统探测默认 autotools | 改写为 CMake 配方（CMakeToolchain + cmake_layout），`CMAKE_SYSTEM_NAME=Linux` 映射 OHOS |
| 3 | 上游测试需联网下载 googletest | CMakeLists.txt.in 用 ExternalProject git clone googletest main | 构建期 BUILD_TESTING=OFF；测试阶段用本地 googletest 1.14.0 源码（复用 metee worktree 缓存）编译运行 |
| 4 | 共享 hmdfs inode 耗尽导致全量 worktree/构建失败 | 并发 executor 大量 worktree 占满 4800 万 inode | worktree 用稀疏 checkout 只物化任务所需路径；构建等待 inode 高峰窗口执行 |

## 源码修改

无源码修改（0 patches）。仅配方层适配：
- conanfile.py 为 CMake 配方（库类型，无 commands.json，符合 R38）
- test_package 为 C++ 消费者测试，通过 find_package(datetime) 链接 `datetime::datetime`，调用公开 API

### 对话 #1（2026-09-22 13:00-13:50，第一轮完整适配）

- init-build 下载官方 tag tarball 成功，SHA-256 核验通过（97ade0d8...bf4facac）
- lang-preflight: cpp 匹配
- 主库 CMake 构建成功（libdatetime.a）
- 上游测试 191/191 通过（datetime 117 + timespan 74）
- 鸿蒙专项测试 tests/test_ohos_datetime.cpp 5/5 PASS
- test_package 消费者测试 1/1 PASS（consumer test OK）
- conan-verify G0-G4/L2/L4/L5 全部通过
- W3 本地 CI 模拟通过（L0/L1/L4/L5 pass；JC 单包口径 pr.diff 通过，其他库基线垃圾经 JUNK_PR_DIFF 隔离）
- 知识查重：候选 E092（CMAKE_SYSTEM_NAME=Linux）、E342（BUILD_TESTING=OFF + 消费者测试）均完整覆盖，路径 A（path_a_no_knowledge）

**编译结束**: 2026-09-22 13:50
**最终状态**: published
---

**编译结束**: 2026-09-22 14:03
**最终状态**: published
