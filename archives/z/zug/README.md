# zug

zug 是一个 C++ transducers 库：可组合、增量式、流式地对顺序容器做归约
（风格接近 Clojure 的 transducer）。全部接口在头文件里，无需链接二进制。

## 功能概述

- **Header-only**：`#include <zug/compose.hpp>` 等即可使用，无 .so/.a
- **可组合管道**：`comp(f, g)` / `f | g`，从右到左组合，支持多参数
- **常用 transducer**：`map` `filter` `take` `drop` `cat` `mapcat` `partition`
  `partition_by` `interpose` `interleave` `enumerate` `scan` `dedupe` `distinct`
  `zip` `unzip` `cycle` `repeat` `replace` `remove` `sink` `iter` `range` `count`
  `product` `random_sample` `read` `write` `readbuf` `writebuf` `eager` `chain`
  `take_nth` `take_while` `drop_while` `map_indexed` `each` `transducer`
- **归约出口**：`reduce` `transduce` `into` `into_vector` `run` 与
  `reducing::first/last/output/emplacing_back`
- **状态协议**：`state_wrapper` `any_state` `state_traits`（增量状态可包装、可解包）
- **依赖**：boost 头文件（`zug/meta/*.hpp` 无条件用 `boost/mpl`；无 `std::variant` 时
  `zug/skip.hpp` 回退 `boost::variant`）

## OHOS 适配

### 特性
- 纯头文件库：`package_type = "header-library"`，包内只有 `include/zug/**` 与许可证
- 上游 50 个 Catch2/CTest 测试程序在配方 `build()` 内构建并执行（层 1 真机 build==host 全量通过；
  交叉构建时只编译不执行，配方会显式 WARNING）
- 消费者只需 `find_package(zug)` + `zug::zug`，boost 由 `transitive_headers` 自动带入

### 已知问题
- 上游 `test/__inline_var_tests/CMakeLists.txt` 漏链 `Catch2::Catch2`，开启
  `zug_BUILD_TESTS` 后该目标编译失败；本包以 1 个补丁修复（见 `0.1.2/patches/`）。
- 上游 `example/` 目录只有一个空的 `examples` 自定义目标，`doc/` 需要 doxygen/sphinx，
  配方默认关闭二者。

### 与 Linux 的差异
- 上游不调用 `find_package(Boost)`，头文件里却是裸的 `#include <boost/...>`：
  由配方把 boost 依赖的 include 目录以 `-isystem` 注入 `CMAKE_CXX_FLAGS`。
- 上游非 MSVC 默认 `-Werror`，OHOS clang15 告警会直接中断构建，故设 `DISABLE_WERROR=ON`。
- 50 个测试目标都是 `EXCLUDE_FROM_ALL`，必须 `cmake.build(target="tests")` 才会编译，
  否则 header-only 包的 `cmake.build()` 是空操作，测试会被静默跳过。
- 不安装上游 `install(EXPORT ZugConfig)`，避免与 Conan 生成的 `zug-config.cmake`
  形成两套 CMake 包文件。

## 依赖关系

### 编译依赖
- boost/1.84.0（公开头文件依赖，随本包传递给消费者）

### 测试依赖
- catch2/2.13.10-r0（仅 `test_requires`，不进消费者依赖链）

## 使用方式

```cmake
# CMakeLists.txt
find_package(zug REQUIRED)
target_link_libraries(my_app PRIVATE zug::zug)
target_compile_features(my_app PRIVATE cxx_std_17)
```

```cpp
#include <zug/compose.hpp>
#include <zug/into_vector.hpp>
#include <zug/transducer/filter.hpp>
#include <zug/transducer/map.hpp>

#include <string>
#include <vector>

int main()
{
    auto v     = std::vector<int>{1, 2, 3, 4};
    auto xform = zug::comp(zug::filter([](int x) { return x % 2 == 0; }),
                           zug::map([](int x) { return std::to_string(x); }));
    auto out   = zug::into_vector(xform, v);   // {"2", "4"}
    return out.size() == 2 ? 0 : 1;
}
```

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [0.1.2](./0.1.2/) | built | 2026-09-19 |

## 参考资料

- GitHub: https://github.com/arximboldi/zug
- 文档: https://zug.readthedocs.io/
- 许可证（BSL-1.0）: https://www.boost.org/LICENSE_1_0.txt
