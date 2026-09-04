# json11 1.0.0 适配笔记

## 编译环境
- 构建系统: cmake（上游同时提供 Makefile 简易 test 目标）
- 编译日期: 2026-09-02
- 编译器: /data/service/hnp/bin/clang / clang++（OHOS toolchain，clang 15.0.4，target aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

json11 为单 .cpp + 单 .hpp 头文件库，无 configure 脚本，官方构建入口为 CMakeLists.txt（cmake_minimum_required 2.8）与 Makefile。

1. 库对象编译（Step2 探索）：
   `clang++ -O2 -std=c++11 -fPIC -fno-rtti -fno-exceptions -I. -c json11.cpp -o json11.o` → exit 0
2. 上游测试二进制编译（Makefile test 目标等价命令）：
   `clang++ -O2 -std=c++11 -fPIC -fno-rtti -fno-exceptions -I. json11.cpp test.cpp -o json11_test` → exit 0
3. 运行上游测试：`./json11_test` → exit 0（全部断言通过）
4. CMake 完整构建（staging）：
   ```
   cmake .. -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
     -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
     -DCMAKE_CXX_COMPILER=$(command -v clang++) -DJSON11_BUILD_TESTS=ON -DCMAKE_CXX_FLAGS=-fPIC
   make -j2                       → exit 0（libjson11.a + json11_test）
   ctest --output-on-failure      → exit 0（上游未注册 CTest 用例，无 tests found，测试经 json11_test 二进制直接运行）
   make install DESTDIR=$TEST_PREFIX → exit 0
   ```
   Staging 产物（$TEST_PREFIX 为 staging 安装前缀）：
   - $TEST_PREFIX$DEFAULT_PREFIX/lib/libjson11.a
   - $TEST_PREFIX$DEFAULT_PREFIX/include/json11.hpp
   - $TEST_PREFIX$DEFAULT_PREFIX/lib/pkgconfig/json11.pc

## 上游测试全量枚举台账

统计口径：全目录（work 源码树完整枚举）。

| 项目 | 类型 | 是否独立上游用例 | 是否实际运行 | 结果/原因 |
|------|------|------------------|--------------|-----------|
| test.cpp | 用户测试源 | 是 — 内含唯一独立测试函数 `JSON11_TEST_CASE(json11_test)`（含注释解析、字面量、序列化、Unicode 转义、parse_multi、容器转 Json 等 ~60 个断言） | 是 | 通过（exit 0） |
| test.cpp 中 `parse_from_stdin()` | 用户测试源辅助函数 | 否 — stdin 解析工具函数（`--stdin` 模式），非独立测试用例 | 否 | 不计入用例数；为命令行工具功能，非测试门禁 |
| json11.hpp | 框架/库头文件 | 否 — 被测库头（232 行） | 编译 | 编译通过 |
| json11.cpp | 框架/库源码 | 否 — 被测库实现（788 行） | 编译 | 编译通过 |
| test.cpp 中 CHECK_TRAIT（static_assert 8 项） | 编译期特性检查 | 否 — 框架宏/编译期断言，非独立 TEST_CASE | 编译 | 编译期通过 |
| CMakeLists.txt | 构建目标定义 | 否 — 构建脚本 | 编译 | 配置+构建通过 |
| Makefile | 构建目标定义 | 否 — 构建脚本（test 目标） | 编译 | 等价命令已复现 |
| json11.pc.in | pkg-config 模板 | 否 — 构建配置 | 生成 | 生成 json11.pc |
| 样例/基准/fixture/测试脚本 | 无 | 无 — 上游无独立 samples/benchmarks/fixtures 目录 | — | 不适用 |

**独立上游用例总数：1**（`json11_test`）
- 实际运行：1
- 通过：1
- 全量通过率：1/1 = 100%

说明：`JSON11_TEST_CASE` 宏在非自定义配置下展开为 `static void name()`（普通函数），上游仅注册 1 个独立测试函数；`parse_from_stdin` 与 CHECK_TRAIT 均非独立用例，已在台账明示。上游 ctest 未注册测试（enable_testing 但无 add_test），测试入口以官方 Makefile 的 `test` 目标为准。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake_minimum_required(VERSION 2.8)` 配置失败 | CMake 4.x 移除对 <3.5 的兼容 | 加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`；conan recipe 将设置该变量 |
| 2 | 编译告警 `unqualified call to 'std::move'` ×11 | 上游代码在 `using namespace std` 下直接 `move()` | 仅告警不影响正确性，保持上游原样，不修改 |

## 源码修改

无（保持上游 v1.0.0 原样，未打补丁；仅验证策略参数层面兼容）。

## 依赖版本

- json11 1.0.0（上游 tag v1.0.0，commit ec4e45219af1d7cde3d58b49ed762376fccf1ace）
- 无第三方运行时依赖（纯标准库 + libc++）

## 验证结果

```bash
cd $BUILD_SRC_DIR
clang++ -O2 -std=c++11 -fPIC -fno-rtti -fno-exceptions -I. json11.cpp test.cpp -o json11_test
./json11_test
# 输出 k1/k3/obj/json_obj_str/points_json 且 exit 0
```
---

**编译结束**: 2026-09-02 23:09
**最终状态**: built
