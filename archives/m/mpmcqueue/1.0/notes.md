# mpmcqueue 1.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only，CMake INTERFACE library）
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4 / clang++（OHOS aarch64 profile）
- 状态: published

## 编译步骤

1. `init-build mpmcqueue 1.0 --url=https://github.com/rigtorp/MPMCQueue/archive/refs/tags/v1.0.tar.gz`
   —— 上游官方标签 `v1.0`（commit 11ffb3cd），10 个文件，header-only 结构确认。
2. `lang-preflight mpmcqueue 1.0` —— detected=cpp，与 task 期望一致，通过。
3. 上游构建验证：`cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5 .. && make && ctest`
   —— MPMCQueueTest 1/1 通过（构造/析构追踪、空满边界、多线程推拉、对齐填充）。
4. `make install DESTDIR=$TEST_PREFIX` —— 产物仅 include/rigtorp/MPMCQueue.h 与
   CMake config（header-only 无二进制）。
5. `conan-init` 生成配方后重写：autotools 模板 → CMake header-only 配方
   （package_type=header-library，generate() 注入 CMAKE_POLICY_VERSION_MINIMUM=3.5
   与 CMAKE_SYSTEM_NAME=Linux，package_info libs=[]）。
6. `conan-verify` —— G0-G4 + L2/L4/L5 全过；test_package 消费者测试
   （入队/出队往返 + 2×2 生产者消费者冒烟）100% 通过。
7. W3 本地 CI 模拟（finish Step5）：setup.sh + build_and_test.sh 通过
   （L0/L1/L1e/L4/L5 pass，L2 skip 因无 bin/），.ci-result.json 已写入。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1.2 报 `Compatibility with CMake < 3.5 has been removed` | 上游 CMakeLists `cmake_minimum_required(3.2)` 过旧 | 配方 generate() 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（等价命中 E187） |
| 2 | `System is unknown to cmake` | CMake 不识别 OHOS 平台 | 注入 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`（等价命中 E092） |
| 3 | test_package 首错 `value of type 'void' is not contextually convertible to 'bool'` | rigtorp MPMCQueue 的 `pop()` 返回 void，`try_pop()` 返回 bool | 消费者测试改用 `try_pop()` 非阻塞拉取并断言总量 |

## 源码修改

无（header-only 库零补丁；patches/ 为空）。

## 依赖版本

无编译期依赖（测试仅用 pthread，CMake find_package(Threads) 系统自带）。

## 验证结果

```bash
ctest --output-on-failure        # 上游 MPMCQueueTest: 1/1 pass
conan-verify mpmcqueue 1.0       # G0-G4 + L2/L4/L5 全过
CI_PACKAGES=archives/m/mpmcqueue/1.0 zsh ci/conan/build_and_test.sh  # EXIT:0, L0/L1/L4/L5 pass
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake header-only 配方（header-library） |
| conandata.yml | 官方源 URL + SHA256（f009ef10…） |
| test_package/ | C++ 消费者测试（test.cpp + CMakeLists + MANIFEST.yml） |
| reports/test-report.md | 验证报告 |
| reports/knowledge-atomicity-audit.md | 知识判定（路径 A）与原子性审计 |

## 注意事项

- 无补丁、无平台宏、无共享框架改动；基线 junk 文件未触碰（JUNK_PR_DIFF prdiff 隔离仅本地验证用）。
- 知识判定：E187/E092 等价命中 → 路径 A（reuse_existing），未创建草稿。
---

**编译结束**: 2026-09-06 22:01
**最终状态**: published
