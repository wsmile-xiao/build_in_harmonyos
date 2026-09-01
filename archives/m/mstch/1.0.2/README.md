# mstch 1.0.2 — HarmonyOS PC Conan 包

C++ implementation of the [Mustache](https://mustache.github.io/) template system.

## 上游信息

| 项目 | 值 |
|------|-----|
| 仓库 | https://github.com/no1msd/mstch |
| Tag | 1.0.2 |
| SHA256 | `811ed61400d4e9d4f9ae0f7679a2ffd590f0b3c06b16f2798e1f89ab917cba6c` |
| License | MIT |

## 包类型

编译型静态库 `libmstch.a`（非 header-only）。源码 `src/*.cpp` 编译为静态归档。

## 依赖

- `boost/1.84.0` — 仅使用 `boost::variant`（header-only，通过 `Boost::headers` 组件）。boost recipe 已传播 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`，规避 musl 下 `pthread_setcancelstate` 缺失。

## 构建目标

- Target: `aarch64-unknown-linux-ohos`
- Compiler: clang 15 + libc++ + C++11
- 产物: `lib/libmstch.a`，`include/mstch/mstch.hpp`

## CMake 目标

```cmake
find_package(mstch REQUIRED CONFIG)
target_link_libraries(my_app PRIVATE mstch::mstch)
```

## 公开 API

```cpp
#include <mstch/mstch.hpp>

mstch::map ctx{{"name", std::string("world")}};
std::string out = mstch::render("Hello {{name}}!", ctx);
// => "Hello world!"
```

## Patches

- `patches/fix-cmake-minimum-version.patch` — 将 `cmake_minimum_required(VERSION 3.0.2)` 提升至 `3.5...3.31`，兼容现代 CMake（CMake 4.x 拒绝 3.0.2）。仅兼容性修复，不修改业务逻辑。

## 上游测试

上游 `mstch_test`（Catch v1.12.2）通过 ctest 执行：

| 指标 | 数值 |
|------|------|
| Total | 65 |
| Passed | 65 |
| Failed | 0 |
| Skipped | 0 |

测试构成（test_main.cpp 逐项核实）：50 个 `MSTCH_TEST` + 8 个 `MSTCH_PARTIAL_TEST`（对应 test/data/ 下 58 个 .hpp）+ 7 个 `SPECS_TEST`（对应 vendor/spec/specs/ 下 7 个 .json）= 65 个 ctest 目标，与 `100% tests passed, 0 tests failed out of 65` 一致。
子模块固定 SHA：Catch=`35f4266d`, rapidjson=`54eb069f`, headerize=`fba2f012`, spec=`83b07216`。

## test_package

消费者测试覆盖：变量替换、HTML 转义、非转义变量、section（truthy/falsy）、列表循环、空列表、反向 section、注释剥离、partials、嵌套上下文（dotted key）。11/11 断言通过。
