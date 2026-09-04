# microsoft-proxy

[microsoft/proxy](https://github.com/microsoft/proxy) 是一个 C++20 header-only 库，
通过 runtime polymorphism（运行时多态）加速 C++ 开发：以编译期定义的 facade 描述接口契约，
在运行时用 `pro::proxy<Facade>` 抽象持有并派发到具体实现，支持就地存储、堆分配、
紧凑存储等多种所有权模型与值语义/引用语义。

## OHOS 适配

- 纯 header-only：无编译期产物，CMake `INTERFACE` 库，安装头文件与 `msft_proxy4Config.cmake`
- 下游消费：`find_package(msft_proxy4)` + `target_link_libraries(... PRIVATE msft_proxy4::proxy)`
- 上游要求完整 C++20 标准库（`std::ranges::uninitialized_copy` 与 `<format>`）；
  OHOS SDK26 libc++ 15.0.4 通过 `_LIBCPP_HAS_NO_INCOMPLETE_FORMAT` /
  `_LIBCPP_HAS_NO_INCOMPLETE_RANGES` 禁用了这两项，需打可移植性补丁（见
  `patches/0001-ohos-libcxx-format-and-ranges-compat.patch`）：
  用标准 `__cpp_lib_format` 特性宏守卫 format skill，并把 5 处
  `std::ranges::uninitialized_copy` 替换为等价的经典 `std::uninitialized_copy`。
  该补丁为 libc 能力探测类（R8 例外），非平台宏，所有工具链均可编译。

## 依赖

- 无第三方运行时依赖（header-only）

## 测试

- 上游 gtest 套件（gtest v1.15.2 + fmt 11.1.4 经 FetchContent）：全量发现 249 个独立
  TEST_CASE；OHOS 工具链可运行子集 107/107 全部通过（100%）；142 个用例因工具链缺失
  `<format>`/ranges/`<memory_resource>` 硬阻塞（详见版本 notes.md 与测试台账）
- 新增 `test_package/ohos_test.cpp`：HarmonyOS 专项真实测试，验证 `__cpp_lib_format`
  守卫与补丁后的 trivial copy/relocate 路径
