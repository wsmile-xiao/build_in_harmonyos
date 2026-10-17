# DRAFT — GTest 1.17 头文件需要 C++17（CTAD/if constexpr），C++11 时代上游测试需 -std=c++17 并同时链接 gmock

基于 tiny-utf8 4.4.3 R01 真实证据（上游 test 目录 6 个 gtest 测试源，GTest 1.17.0 官方 v1.17.0 tag）

## 问题描述

C++11 时代的三方库（如 tiny-utf8，header-only）上游测试用新版 GoogleTest（1.17.0）时，
在 OHOS/arm64 clang 工具链下编译测试目标报两类错误：

1. **C++17 特性要求**：`gtest-param-test.h` 使用 C++17 的类模板实参推导（CTAD）
   `std::function(std::declval<Func>())` 与 `if constexpr`：

   ```
   error: use of class template 'function' requires template arguments
     typename StdFunction = decltype(std::function(std::declval<Func>()))>
   warning: constexpr if is a C++17 extension [-Wc++17-extensions]
   ```

   而上游 `test/CMakeLists.txt` 通常钉 `CXX_STANDARD 11`（或 14），导致编译失败。

2. **gmock 头缺失**：上游测试 helpers（如 `helpers_ssotestutils.h`）若
   `#include <gmock/gmock.h>`，仅构建/安装 GTest（BUILD_GMOCK=OFF）时：
   ```
   fatal error: 'gmock/gmock.h' file not found
   ```

## 根因

- GTest ≥1.14 的头文件（尤其 `gtest-param-test.h`）已使用 C++17 语法（CTAD、if constexpr）
- 上游库的测试 CMake 配置按库自身的 C++ 标准（C++11）编译测试目标，与新 GTest 头不兼容
- 测试辅助代码引用 gmock 头，但 GTest-only 安装不含 gmock

## 解决方案

**仅对上游测试编译使用 `-std=c++17`（库本体仍按 C++11），并同时构建+链接 gmock：**

```bash
# 1. GTest 1.17 本地构建（含 gmock）:
cmake -S googletest-1.17.0 -B build-gtest \
      -DBUILD_GMOCK=ON -DCMAKE_CXX_STANDARD=17 -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=$GT
cmake --build build-gtest -j4 && cmake --install build-gtest

# 2. 上游测试编译（cwd=库源码根）:
clang++ -std=c++17 -O2 -I include -I $GT/include -I test/src \
  test/src/*.cpp test/src/mocks/*.cpp test/src/helpers/*.cpp \
  $GT/lib/libgtest.a $GT/lib/libgtest_main.a $GT/lib/libgmock.a -pthread \
  -o tinyutf8_test

# 3. 运行:
./tinyutf8_test    # tiny-utf8 实测 16/16 全部 PASSED
```

## 验证

- tiny-utf8 4.4.3：16 个独立上游 TEST 用例编译并全部运行通过（exit 0）
- 日志 SHA-256: e8e7fd225065358032776d72d324a961a7b19486956d4f8546c4345858c3a22f

## 适用边界 / 反例

- 适用：GTest 头含 C++17 特性（≥1.14）且上游测试按 C++11/14 编译的库
- 反例：旧版 GTest（无 CTAD/if constexpr）或上游测试已按 C++17 编译时不需此处理
- 库本体标准不受影响（-std 只作用于测试编译）

## 查重差异

- E096（cmake c++17 显式声明，abseil）、E130（libcxx-ohos nullptr_t）、E293（C++17 遗留特性移除）
  —— 均非"GTest 头要求 C++17"主题
- DRAFT-ctre（header-only 配方四要点）—— 覆盖 profile libstdc++/CMakeToolchain 等，
  未覆盖 GTest 头 C++17 + gmock 缺失
- E332/E342（gtest_discover_tests 离线/联网）—— 机制不同

*由 tiny-utf8 4.4.3 R01 生成（2026-09-05），知识候选台账见 .oh-executor/tiny-utf8-r01-knowledge-ledger.log*
