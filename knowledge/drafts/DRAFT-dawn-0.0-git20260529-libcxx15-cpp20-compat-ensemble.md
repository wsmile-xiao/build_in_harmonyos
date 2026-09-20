# OHOS clang15/libc++15 的 C++20 兼容全谱处理（大型 C++ 库）

> DRAFT — dawn 0.0-git20260529.432db5d7 适配产出，待知识库审核提升
> 关联 .kv: `DRAFT-dawn-0.0-git20260529-libcxx15-cpp20-compat-ensemble.kv`

## 问题

dawn（WebGPU 参考实现，Chromium 生态，8 万余源文件）在 HarmonyOS PC
（OHOS SDK26 + clang 15 + libcxx-ohos15）上编译/链接/测试暴露了
**一整族 C++20 兼容缺口**，单靠既有知识条目无法覆盖：

1. `std::ranges::copy/reverse/equal/search`、`std::views::filter/values`
   不存在（libcxx15 未实现 C++20 ranges/views）；
2. `std::format` 不存在（`<format>` 为空 stub）；
3. `std::lexicographical_compare_three_way` 不存在（spaceship 部分缺失）；
4. `std::span` 无法从 `std::string_view` 直接 CTAD；
5. C++20 聚合括号初始化 **P0960** 不被支持：`TableAndExpected(a, b)` 报
   "no matching constructor"，必须改 `TableAndExpected{a, b}`；
6. lambda 无法按引用捕获结构化绑定：`auto [x, y] = ...; [&]{ use(x); }`
   报 "reference to local binding"；
7. 依赖类型上下文缺 `typename`（clang 15 严格）：`Base::reference`、
   `Sha3<T>::Output`、`Traits::MutexType`、`ForwardToServerHelper<F>::Userdata`；
8. `overloaded{...}` 聚合 CTAD 不生成 deduction guide（须显式补）；
9. CMake `bundle_libraries` 把 conan **IMPORTED** 静态库（abseil）的 `.a`
   作为成员嵌入 `libwebgpu_dawn.a` → lld "archive member is neither ET_REL
   nor LLVM bitcode" + undefined absl 符号（E236 只覆盖 libtool `.la` 场景）；
10. gtest 通用分支硬编码 `/tmp`（只读，E002 族）导致测试失败。

## 根因

OHOS SDK26 自带 libc++15 未实现或仅部分实现 C++20 标准库设施，且
clang 15 对若干 C++20 语言特性（P0960、结构化绑定捕获、依赖类型
typename、聚合 CTAD）支持不完整。上游 dawn 基线使用更新的 clang/libc++，
因此按新版标准书写的代码在 OHOS 工具链上全部暴露。

## 方案（可跨库复用）

### A. 经典算法替换（ranges/format/views/spaceship）

| 缺失设施 | 替换 |
|----------|------|
| `std::ranges::copy(r, d)` | `std::copy(r.begin(), r.end(), d)` |
| `std::ranges::reverse(c)` | `std::reverse(c.begin(), c.end())` |
| `std::ranges::equal(a, b)` | `std::equal(a.begin(), a.end(), b.begin())` |
| `std::ranges::search(h, n)` | `std::search(h.begin(), h.end(), n.begin(), n.end())` |
| `std::views::filter/values` | 直接 for 循环 + 条件/结构体成员 |
| `std::format("x{}", n)` | `"x" + std::to_string(n)` 或流拼接 |
| `lexicographical_compare_three_way` | 手工 `for` 三路比较返回 `std::strong_ordering` |
| `std::span{sv}`（string_view CTAD） | `std::span(reinterpret_cast<const std::byte*>(sv.data()), sv.size())` |

### B. 语言特性兼容

- **P0960**：聚合体 `Type(a, b)` → `Type{a, b}`（大括号初始化可用）。
- **结构化绑定捕获**：`auto [x, y] = ...` 改为
  `auto item = ...; auto x = item.first; auto y = item.second;` 再在 lambda 中引用。
- **依赖类型 typename**：模板上下文中 `X<T>::member` 补 `typename`。
- **overloaded**：`struct overloaded : Ts... { using Ts::operator()...; };`
  后补 `template <class... Ts> overloaded(Ts...) -> overloaded<Ts...>;`。

### C. CMake bundle 修复（conan IMPORTED 依赖）

`bundle_libraries` 收集对象时**跳过 IMPORTED 目标**：

```cmake
get_target_property(is_imported ${dep} IMPORTED)
if(NOT is_imported AND (type STREQUAL "STATIC_LIBRARY" OR type STREQUAL "OBJECT_LIBRARY"))
  list(APPEND all_objects $<TARGET_OBJECTS:${dep}>)
endif()
```

配套 conan 配方：
- `requirements()` 用 `visible=False`（构建期依赖不向消费者传递 find_dependency）；
- `package_info()` 用 `ignored_requires`；
- test_package 显式链接 abseil 全库：`file(GLOB ABSL_STATIC_LIBS "${ABSEIL_LIB_DIR}/libabsl_*.a")`
  + `target_link_libraries(test_dawn dawn::dawn ${ABSL_STATIC_LIBS})`；
- 测试源用 `.cpp` 并启用 CXX 语言（否则 C 链接缺 libc++ 符号）。

### D. gtest 只读 /tmp（E002 族）

`gtest-port.cc` 通用分支尊重 `TMPDIR`：

```cpp
const char* t = getenv("TMPDIR");
name_template = (t && *t) ? t : "/tmp/";
if (name_template.back() != '/') name_template.push_back('/');
```

### E. CMake 无 OHOS 平台模块（E092 族）

`generate()` 设 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`，
显式关闭 `DAWN_USE_X11/GLFW/Vulkan/GL/Metal/D3D` 等后端。

## 验证（dawn 实测）

- conan create（W3 门禁）PASS，test_package 真实调用
  `wgpuCreateInstance/wgpuInstanceRelease` PASS；
- 上游测试全量运行：
  - `tint_unittests` 44484/44484（1073 套件）100%；
  - `dawn_end2end_tests` 292/292（Null 后端）100%；
- 日志: `archives/d/dawn/0.0-git20260529.432db5d7/reports/tint-unittests.log`
  （sha256 0b7cae64…）、`dawn-end2end-tests.log`（sha256 7c281b8d…）。

## 适用边界 / 反例

- 仅适用于**工具链缺设施**的兼容替换；若上游依赖 ranges 性能语义（lazy
  evaluation）需保留 ranges，应等待 libc++ 升级而非替换。
- P0960 大括号替换仅在聚合体/无歧义时有效；含显式构造函数的类型不受影响。
- bundle 跳过 IMPORTED 仅对"消费者自行链接依赖"的静态库有效；若目标包
  必须自包含（header-only 内嵌依赖）则不可跳过。
- gtest TMPDIR 补丁在 `/tmp` 可写的普通 Linux 上无副作用（回退原路径）。

## 查重差异（七轴摘要）

- exact_duplicate: 否；causal_duplicate: 部分（ranges/format/spaceship 与
  既有草稿同根因）；trigger_overlap: 部分；solution_overlap: 部分（经典
  算法替换一致）；
- combination_novelty: 是（单一大型库全谱系统性处理）；
- boundary_novelty: 是（P0960、结构化绑定捕获、IMPORTED bundle 三条新边界）；
- test_migration_novelty: 是（44776 用例全量证据链 + gtest TMPDIR 补丁）。

**决定**: new_draft — 新增差异已由真实日志验证且可跨库复用。
