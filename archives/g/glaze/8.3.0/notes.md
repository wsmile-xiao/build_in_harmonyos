# glaze 8.3.0 OHOS 适配笔记

## 编译环境

- 设备: OpenHarmony PC（aarch64），OHOS SDK 26 clang 15.0.4 / libc++ 15
- 构建: GNU Make 4.4.1 + CMake 4.1.2，Git 2.45.2，Conan 2.29.1
- 全局 python3: /data/service/hnp/bin/python3（3.12.8）
- 状态: built（设备构建与全部验证通过）

## 上游版本与源码

- 上游: https://github.com/stephenberry/glaze v8.3.0
- tarball: v8.3.0.tar.gz，SHA-256
  `6a8f97f5cdb8df5c87f1b32710679585f3f1a577b67bb66150f2516072e00317`
  （GitHub 直连与 ghfast 镜像双源下载逐字节一致后锚定）

## 核心结论

glaze 8.3.0 为 C++23 header-only INTERFACE 库，上游要求
`target_compile_features(glaze::glaze INTERFACE cxx_std_23)`。OHOS 工具链为
clang 15 / libc++ 15 / profile cppstd=17。头文件库本体无需编译；本任务完成了：

1. 上游全量原生构建（162 个目标）+ CTest 注册的 87 项测试 **100% 通过**；
2. clang15/libc++15 可移植性补丁集（18 个库头文件 + 9 个测试源）；
3. Conan 配方（上游 CMake install 模式）+ 真实消费者 test_package；
4. 下游最低标准声明（C++23）与 cppstd=17 profile 的协同。

## 上游测试统计（设备实跑）

- CTest 注册 87 项全部通过（`100% tests passed, 0 tests failed out of 87`）
- 其中 73 项 ut 套件框架自报：tests **6847/6847**、asserts **831365/831365**
  （含 json_test_non_null 等同源双配置变体的重复执行）
- float_write_test 自报 99615 次随机有限浮点往返通过
- streaming_rejects_* 9 项为编译期拒绝测试（目标必须构建失败才通过），全部通过
- 取数命令与逐套件清单见 test_package/MANIFEST.yml

## 平台适配要点

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `#include <expected>` 编译失败 | libc++ 15 无 std::expected（libc++ 16 起提供） | 恢复上游 v4.4.3 时代自带的 MIT `glz::expected` 回退实现（`__cpp_lib_expected` 特性宏守卫），并补 `glz::is_expected` concept；tests 中 6 处 `std::expected` 引用同步改为 `glz::expected` |
| 2 | `(void)(lambda.template operator()<I>(), ...)` 解析错误 | clang 15 对 `(void)(...fold...)` 形态的解析缺陷（12 行可复现） | 等价改写为 `((void)lambda.template operator()<I>(), ...)` |
| 3 | constexpr 函数内 `static constexpr` 局部变量 | C++23 P2647（clang 16 才支持） | 值语义处去 static；需要静态存储期（string_view 指向）处用上游 v4.4.3 的 `make_static` 惯用法；运行期 lambda 内合法的保持原样 |
| 4 | `reflect<T>::template elem<I>` 解析失败 | clang 15 依赖上下文别名声明解析缺陷 | 加 `typename`（全标准可移植） |
| 5 | `ranges::sort/adjacent_find/any_of` 缺失 | 该 OHOS SDK 的 libc++ 15 `<algorithm>` 无 ranges 算法 | 降级为语义等价的 `std::sort/std::adjacent_find/std::any_of` 迭代器版本 |
| 6 | `make_unique_for_overwrite` / `ranges::copy` / `<format>` 缺失 | libc++ 15 无对应 C++20/23 库设施 | 测试源等价替换（`unique_ptr<char[]>(new char[N])`、`std::copy`、snprintf oracle） |
| 7 | 默认化 `operator<=>` 报 implicitly deleted | libc++ 15 的 std::string 无 `<=>` | 测试类型改显式 `compare()` 三路比较 |
| 8 | `std::lexicographical_compare_three_way` 缺失 | C++20 库算法 libc++ 15 未实现 | inplace_vector 与测试中等价手写三路比较 |
| 9 | lambda 捕获结构化绑定失败 | P1091（clang 16 才支持） | 绑定别名/副本后再捕获（stencil/toml 共 3 处） |
| 10 | `convert_struct` 误报不可转换 | clang 15 对 else 分支中 `static_assert(false_v<...>)` 的求值缺陷（分支未进入也报错） | 改为立即调用 lambda 内 `static_assert(Flag)` 的依赖式断言；真实不可转换场景仍正确触发 |
| 11 | `array_apply_t{Adapter(v)}` CTAD 失败 | P1816 聚合 CTAD（clang 17 才支持） | 补显式推导指引 `array_apply_t(A) -> array_apply_t<A>` |
| 12 | JMESPath 编译期 token 解析失败 | libc++ 15 的 `std::from_chars` 非 constexpr（P2291，libc++ 16 起支持） | `parse_int` 改为等价 constexpr 手写十进制解析（含越界拒绝） |
| 13 | `std::span<const char>` 被当 char 数组写出 | 上游依赖 C++23 P1989 string_view range 构造使 `str_t<span<char>>` 成立；libc++ 15 无 | `str_t` 概念补 1 字节 char span 子句（与上游 clang17 上的有效行为一致） |
| 14 | `{:.80f}` 等 >64 字节浮点格式报 unexpected_end | snprintf 回退分支把 unchecked 预算写死 64 字节，与调用方 `write_padding_bytes=256` 预分配不符 | 预算改为 `glz::write_padding_bytes`（恢复上游 std::format 路径的等价容量假设） |

## 修改上游测试的说明

以下测试源为工具链可移植性做了等价替换（PR 中如实申报）：

- beve_test/cbor_test/json_test/jsonb_test：`std::expected` → `glz::expected`、
  `#include <expected>` → `glaze/util/expected.hpp`
- beve_test：`std::ranges::sort` → `std::sort`
- cbor_test：`make_unique_for_overwrite` → `unique_ptr(new char[])`
- json_test：asan/immutable 用例的 `make_unique_for_overwrite`、`ranges::copy`、
  `emplace_back(1, 1.1f)`（P0960 聚合括号初始化）等价替换；custom_struct/StringKey
  显式比较集
- json_variant_support_test：StringKey 比较集
- embedded_null_test：custom_string `<=>` 用 `compare()`
- inplace_vector_test：`lexicographical_compare_three_way` 自比较 → `equal`
- snprintf_fallback_test：`std::format` oracle → 等价 `snprintf` oracle（本测试
  的验证目标就是 printf 转换一致性，oracle 语义不变）
- stencil_test：`make_unique_for_overwrite` 等价替换

## 依赖与排除项（均有上游依据）

- 测试框架 ut v1.2.1（openalgz/ut）从源码构建，为其补了 libc++15 的
  `std::source_location` 回退（仅测试基础设施，不进包）
- asio asio-1-36-0、Eigen 3.4.0 由 FETCHCONTENT_SOURCE_DIR 离线提供
- 排除项：networking_tests（无 OpenSSL）、jsonb_sqlite_test（上游 find_package
  自动跳过）、simple_float_test / yaml_conformance_data / p2996_test /
  eetf_test（上游默认 OFF）、fuzzing（dev-mode 附加项，需 libfuzzer 与 net 栈）

## 验证结果

```bash
# 上游构建（j4，用户已授权并行度）
cmake -S $SRC -B $BUILD -DCMAKE_BUILD_TYPE=Release -Dglaze_DEVELOPER_MODE=ON \
  -DBUILD_TESTING=ON -Dglaze_ENABLE_SANITIZERS=OFF -Dglaze_BUILD_NETWORKING_TESTS=OFF \
  -Dglaze_ENABLE_FUZZING=OFF -DFETCHCONTENT_FULLY_DISCONNECTED=ON
cmake --build $BUILD -j4          # 162 目标全部构建成功
ctest --output-on-failure          # 100% tests passed, 0 tests failed out of 87
```

## 下游最低标准

- 上游要求 C++23（cxx_std_23）。本包 `cpp_info.cxxflags = ["-std=c++2b"]` 使
  CMakeDeps 下游在 cppstd=17 profile 下自动获得 C++23；下游也可显式设置
  `CMAKE_CXX_STANDARD 23`。
- package_id 仍按 profile cppstd=17 生成（header-library 无编译产物，行为与
  profile 解耦）。
