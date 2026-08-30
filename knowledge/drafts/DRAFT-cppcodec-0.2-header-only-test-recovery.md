# DRAFT-cppcodec-0.2-header-only-test-recovery

header-only C++ 库多编码默认别名头冲突的命名头规避 + 测试入口恢复
（Catch2 submodule 缺失 / 老 CMake 最低版本兼容）
Conan 2.29.1 + clang 15 + CMake 4.1.2

- **ID**: DRAFT-cppcodec-0.2-header-only-test-recovery
- **触发工具**: clang / cmake / conan / test
- **阶段**: compilation / testing / source
- **严重度**: 🟡 blocking (2)
- **分类**: headers, cmake, testing, conan, ohos

---

## 问题（Problem）

cppcodec 0.2 是 header-only 多编码 C++11 库（base64 / base64url / base32 /
hex）。R01 首轮 smoke test（消费者测试 `test_cppcodec.cpp`）首次编译失败：

1. **多编码默认别名头冲突**：同时包含 `base64_default_rfc4648.hpp` 与
   `base64_default_url.hpp` 时，同一命名空间内 `using base64` 分别定义为
   `cppcodec::base64_rfc4648` 与 `cppcodec::base64_url`，编译器报
   `type alias redefinition with different types`。
2. **上游 Catch2 submodule 缺失**：`test/test_cppcodec.cpp` 依赖 Catch2
   （`.gitmodules` 指向 Catch2，tag v0.2 对应 v2.3.0），release tarball 内
   `test/catch/` 是空 submodule，上游 CMake 的 bundled 路径
   `catch/single_include` 为空 → 测试入口无法构建。
3. **老 CMake 最低版本**：上游 `CMakeLists.txt` 声明
   `cmake_minimum_required(2.8.5)`，现代 CMake（4.x）已移除 <3.5 兼容，
   配置阶段直接报错退出。

**错误特征**：`type alias redefinition with different types` |
`using base64 = cppcodec::base64_url` | `base64_default_*` |
`test/catch` | `single_include/catch.hpp` |
`Compatibility with CMake < 3.5 has been removed` |
`cmake_minimum_required.*2.8`

---

## 根因（Root Cause）

1. cppcodec 每个编码同时提供 **default 别名头**（`base64_default_rfc4648.hpp`
   等，在库命名空间内定义 `using base64 = ...`）与 **命名头**
   （`base64_rfc4648.hpp` 等，提供 `cppcodec::base64_rfc4648` 实体）。
   两个 default 头在同一翻译单元共存必然导致别名重定义。
2. release tarball 不包含 git submodule 的实际内容，`test/catch/` 目录为空；
   上游 CMake 找不到系统 Catch2 时回退到 bundled `single_include`，空目录
   使 `#include <catch2/catch.hpp>` 无法解析。
3. CMake 4.x 移除对 `cmake_minimum_required(VERSION < 3.5)` 的兼容模式支持，
   旧项目直接退出（与既有知识 E103/E187 一致，本条目不重复沉淀该主题）。

**影响范围**：header-only 多编码 C++ 库（同一命名空间提供 default 别名头
与命名头）的 test_package 消费者测试；release tarball 含空 git submodule
的上游测试恢复；声明老 CMake 最低版本（<3.5）项目的本地验证。

---

## 方案（Solution）

1. **命名头规避**：消费者测试只包含命名头
   （`base64_rfc4648.hpp` / `base64_url.hpp` / `base32_rfc4648.hpp` /
   `hex_lower.hpp`），绝不同时包含多个 default 别名头；需要多种编码时
   显式 `using my_b64 = cppcodec::base64_rfc4648;`。
2. **测试入口恢复**：将官方 Catch2 对应版本（v0.2 → v2.3.0）的
   `single_include` 放入上游 CMake 期望的 `test/catch/single_include`
   路径（上游在未找到系统 Catch2 时
   `include_directories(${CMAKE_CURRENT_SOURCE_DIR}/catch/single_include)`，
   测试源 `#include <catch2/catch.hpp>`）。
3. **老 CMake 兼容**：配置时加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
   （既有知识 E103/E187 已覆盖，仅在本条目作为验证命令引用）。

```bash
# 1) 命名头消费者测试（test_package/test_cppcodec.cpp）
clang++ -std=c++11 -I <src> archives/c/cppcodec/0.2/test_package/test_cppcodec.cpp \
    -o test_cppcodec && ./test_cppcodec
# 预期: PASS: cppcodec header-only consumer test OK

# 2) 恢复上游 Catch2 测试入口
mkdir -p <src>/test/catch/single_include
cp -r Catch2-2.3.0/single_include/* <src>/test/catch/single_include/

# 3) 构建并运行上游测试
cmake -S <src> -B build -DBUILD_TESTING=ON -DCMAKE_CXX_STANDARD=11 \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    && cmake --build build --target test_cppcodec \
    && ctest --test-dir build
# 预期: 100% tests passed, 1/1 (8 test cases / 587 assertions, clang 15 实测)
```

---

## 验证（Verification）

- smoke test：`clang++ -std=c++11` 编译运行 test_package，exit 0，输出
  `PASS: cppcodec header-only consumer test OK`（覆盖 base64/base64url/base32/hex 往返）。
- 上游测试：`cmake ... -DCMAKE_POLICY_VERSION_MINIMUM=3.5` 配置→构建→
  `ctest` 1/1 PASS，`All tests passed (587 assertions in 8 test cases)`。
- 鸿蒙特有：`aarch64-unknown-linux-ohos-clang++` 编译运行，`__OHOS__`/
  `__aarch64__` 平台宏断言 + 编码往返，PASS。
- 一致性：本 `.md` 与 `DRAFT-cppcodec-0.2-header-only-test-recovery.kv`
  的 `error_signature`、`root_cause`、`rec_approach`、`affected_scope`、
  `verification_cmd` 逐项一致（配对审计）。

## 适用边界 / 恢复条件（Scope & Recovery）

- **适用**：header-only 多编码库的消费者测试；含空 submodule 的 release
  tarball 测试入口恢复；`cmake_minimum_required(<3.5)` 项目本地验证。
- **不适用**：单一编码 default 头正常使用；已有系统 Catch2 且上游优先
  使用系统包（此时无需 bundled single_include）；已升级 CMakeLists 最低
  版本的库。
- **恢复条件**：若 conan create / CI 又出现 `catch.hpp not found`，检查
  `test/catch/single_include/catch2/catch.hpp` 是否就位、Catch2 版本是否
  与上游 `.gitmodules` 一致；若 `type alias redefinition` 复现，检查
  test_package 是否误包含两个 default 头。
- **查重差异**：`similar_to` = E103 / E187（二者只覆盖"CMake 4.x 移除
  <3.5 兼容"一条），本条目新增"多编码 default 别名头冲突的命名头规避"与
  "Catch2 submodule 缺失用官方 single_include 恢复测试入口"两个增量主题，
  与 pico-sdk 空 submodule（嵌入式 SDK 目录占位）及 protozero header-only
  （NDEBUG 消费者陷阱）均不同。

## 作者

- Agent: pc3-37 (AtomCode)
- 日期: 2026-08-29
- 来源事件: cppcodec 0.2 R01 bootstrap + R02 formal adaptation
- 知识类型: 新增草稿，不预占正式 E 编号；promote 决策由人工审核决定。
