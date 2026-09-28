# CMake 已编译产物 ≠ Conan 已声明组件：boost `package_info()` 漏登记 `serialization` 导致 `Boost::serialization` target 缺失

## 现象

在 `build_in_harmonyos` 仓库里用 `conan create` 出 `boost/1.90.0.4.2` 后，下游包（sfcgal 2.3.0）在 CMake configure 阶段报：

```
CMake Error: Could not find a package configuration file provided by "Boost"
  Requested: Boost REQUIRED COMPONENTS ... serialization ...
CMake Error at CMakeLists.txt:xxx (add_executable):
  target "xxx" links to target "Boost::serialization" but the target was not
  found. Perhaps a find_package() call is missing ...
```

但手动 `ls $CONAN_HOME/p/boost*/lib/` 时，`libboost_serialization.so` **明明在**包里。

## 根因

Boost 的 Conan 配方里，「编哪些库」和「导哪些 Conan 组件」是**两段独立的代码**：

1. `generate()` 里把模块名塞进 `BOOST_INCLUDE_LIBRARIES`，交给上游 CMake 决定编译哪些 `.so`；
2. `package_info()` 里手写一个组件名元组循环，给每个名字 `set_property("cmake_target_name", "Boost::<name>")`，CMakeDeps 才会生成对应 target。

`boost/1.90.0.4.2` 的 `BOOST_INCLUDE_LIBRARIES` 字符串里**早就有** `serialization`（因为 pinocchio 4.1.0 需要），所以 `libboost_serialization.so` 从 1.90.0.2 起就被编译进包；但 `package_info()` 的循环元组是：

```python
for name in ("atomic", "container", "filesystem", "program_options",
             "system", "unit_test_framework"):
```

里面**没有 serialization**。结果就是：产物在 `lib/`，`collect_libs()` 能扫到，但 Conan 没把它登记成 `cpp_info.components["serialization"]`，CMakeDeps 不生成 `Boost::serialization`。下游 `find_package(Boost COMPONENTS serialization)` 直接失败。

这是典型的「**构建系统产物集合**」与「**Conan 组件声明集合**」漂移——两边维护两个列表，加新库时只动了一边。

## 通用排查法（三层核对）

下游找不到 `Foo::bar` target 时，按这个顺序查，不要急着 patch 上游：

1. **库到底编出来没有**：`ls <package>/lib/libfoo_*.so`。没有 → 是构建侧（`BOOST_INCLUDE_LIBRARIES` / `find_modules` / options）问题。
2. **Conan 把它登记成组件没有**：看配方 `package_info()` 里 `cpp_info.components[<name>]` 的循环元组，以及 `cmake_target_name`。有 `.so` 但没组件 → 就是本案例，补登记即可。
3. **下游用的 target 名跟配方导出的对得上吗**：`cmake_target_name` 写的是 `foo::foo` 还是 `Foo::Foo`？这是另一个常见漂移（见 sfcgal 的 CGAL shim 草稿）。

## 修复

本版 `1.90.0.4.3` 与 `1.90.0.4.2` **同源码、同补丁、同 sha256**，唯一改动是 `package_info()` 循环里加 `"serialization"`，并声明其编译型依赖 `requires=["system"]`（其余 mpl/utility/typeof 全 header-only，由 `Boost::headers` 覆盖）。**零新编译**——`.so` 早就在包里，只是补一张目录。

## 验证

新增消费者用例 `test_package/test_boost_serialization.cpp`：
`find_package(Boost COMPONENTS serialization)` + 链接 `Boost::serialization` + 一次 `vector<int>` 的 `binary_oarchive → binary_iarchive` 往返断言。configure 阶段就能拦住「target 缺失」这类回归。

## 教训

- Boost 这类「库多、组件碎」的 C++ 配方，`BOOST_INCLUDE_LIBRARIES` 和 `package_info()` 组件列表**必须放在一起 review**，缺一边都会出现「`.so` 在但 target 不在」的幽灵依赖。
- 给一个已有版本「补组件」时，**升 patch 号出新版本**（1.90.0.4.2 → 1.90.0.4.3），不要改老版本目录——老版本已被别的 PR 合入并构建，动它会破坏既有 consumer。
