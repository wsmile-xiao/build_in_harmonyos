# E700 — 上游 CMakeLists set(CMAKE_CXX_STANDARD 11) 硬编码 + 测试代码 C++17 特性 → -Wc++17-extensions 硬错误

## 错误特征

```
error: use of class template 'std::array' requires template arguments
error: 'if' initialization statements are a C++17 extension [-Werror,-Wc++17-extensions]
```

典型场景：CMake 项目根 CMakeLists 声明 `set(CMAKE_CXX_STANDARD 11)`，测试源使用
C++17 特性（CTAD `constexpr std::array access_order = {...}`、if 初始化语句），
测试目标带 `-Wall -Wextra -Wpedantic -Werror`，在默认标准 <17 的工具链
（OHOS clang 15 默认 gnu++14；gcc 9/10/11 默认 gnu++14）下编译失败。

## 触发条件

- 构建系统: cmake
- 阶段: compilation（测试目标）
- 工具链: clang 15（OHOS）、gcc <12、其他默认标准 <C++17 的编译器

## 根因分析

上游 `set(CMAKE_CXX_STANDARD 11)` 硬编码 C++11，但测试代码实际需要 C++17。
上游 CI 用现代 clang/gcc（默认 C++17）因此全绿；问题只在默认标准 <17 的
工具链暴露（OHOS clang 15 默认 gnu++14 + `-Wc++17-extensions` 因 `-Werror`
升级为硬错误）。

关键机制：`set(CMAKE_CXX_STANDARD 11)` 写入 CMakeLists 后是普通变量，会**覆盖**
命令行 `-DCMAKE_CXX_STANDARD=17` 的 cache 变量——仅加 `-D` 无效；必须让
`-std=c++17` 出现在编译命令后段（`CMAKE_CXX_FLAGS`）或直接改 `set()` 值。

## 解决方案

### 推荐方案

1. **最简（验证用）**：`cmake -S . -B build -DCMAKE_CXX_FLAGS="-std=c++17"`——flags
   位于编译命令后段，压过 `set(CMAKE_CXX_STANDARD 11)` 生成的 `-std=gnu++11`。
2. **配方侧**：conanfile `generate()` 用 CMakeToolchain 显式设置
   `CMAKE_CXX_STANDARD=17` + `CMAKE_CXX_STANDARD_REQUIRED=ON`；或在 test_package
   的 `target_link_libraries` 目标上 `set_target_properties(... CXX_STANDARD 17)`。
3. **补丁侧**：将 CMakeLists 的 `set(CMAKE_CXX_STANDARD 11)` 改为 17。

验证：`cmake --build . -j4 && ctest` → 35/35 通过（caches 0.1.1 实测）。

### 禁止做法

- ❌ 仅 `-DCMAKE_CXX_STANDARD=17`（被 CMakeLists 的 `set()` 覆盖，无效）
- ❌ 直接去掉 `-Werror` 掩盖问题（上游测试的 `-Werror` 是其质量门禁，且 CI 同源）
- ❌ 认为「库本体是 C++11 所以测试也能过」（测试代码与库本体标准需求可以不同）

## 适用边界 / 反例

- 适用：默认标准 <C++17 工具链 + CMakeLists 声明 C++11 + 测试代码 C++17 特性的项目。
- 反例：工具链默认已是 C++17（现代 clang/gcc 17+）时不会触发；库本体使用 C++17
  且 CMakeLists 正确声明时不会触发。

## 关系

- `similar_to`: E096（cmake-cxx-standard-explicit：CMake 特性检测失败需显式标准）、
  E130（change-cxx-standard：OHOS libc++ 需 C++17）、E293（旧代码 C++17 移除特性）。
- 差异：E096 根因是 CMake 检测编译器特性失败（System is unknown to cmake）；
  E130 根因是 OHOS libc++ 头文件需 C++17；E293 是旧代码在 C++17 下移除的
  throw()/register。本条目的独特点：**CMakeLists `set()` 覆盖 `-D` cache 变量**
  的机制 + 测试代码标准高于库本体声明的典型形态。

## 验证证据

caches 0.1.1 上游 35 个 TEST 用例以 OHOS clang 15 + `-std=c++17` 构建后
ctest 4/4 全过（35/35，100%），见 archives/c/caches/0.1.1/reports/test-report.md。
