# DRAFT-libfex-0.1.0-std-expected-polyfill-libcxx15

> Path B 知识库扩展草稿（与 libfex 0.1.0 归档同一 PR 交付）
> 配对文件: `DRAFT-libfex-0.1.0-std-expected-polyfill-libcxx15.kv`

## 症状

编译任何 `#include <expected>` 的 C++23 库时，OHOS 工具链（clang 15.0.4 +
libc++ 15.004，`_LIBCPP_VERSION 15004`）报：

```
fatal error: 'expected' file not found
#include <expected>
         ^~~~~~~~~~
1 error generated.
```

且 clang-15 不接受 `-std=c++23` 字面量（只认 `-std=c++2b`）：

```
error: invalid value 'c++23' in '-std=c++23'
```

若在 Conan 配方里写 `CMAKE_CXX_STANDARD=2b`，CMake 会在 project() 的 ABI
try_compile 处报：

```
Target "cmTC_*" requires the language dialect "CXX2b"
```

## 根因

- OHOS SDK（ohos-sdk_26.0.0.18）libc++ 版本 15，`<expected>` 头自 libc++ 17
  才提供；C++23 的 `std::expected`/`std::unexpected` 在该工具链上整头缺失。
- clang-15 前端对最终标准名 c++23 尚未落地，使用草案名 c++2b。
- CMake 的 `CMAKE_CXX_STANDARD` 只接受数值（23），不接受字符串 "2b"。

对**公共 API 直接暴露 `std::expected`** 的库（如 libfex：filesystem.hpp /
session.hpp / types.hpp 的回调签名全是 `std::expected<T, Errc>`）：

1. 不能套用 glaze/8.3.0 的"改 `glz::expected` 命名空间"方案——公共 API
   的 ABI/源码契约被破坏，消费者也无法编译通过；
2. 因此必须以 polyfill 头注入 **namespace std**，保住 `std::expected` API。

## 方案（libfex/0.1.0 实证）

1. 新增 `include/fex/expected_compat.hpp`（MIT 单头 std::expected 实现，
   Rishabh Dwivedi，1502 行）：

   ```cpp
   #pragma once
   // ... license, <utility>, <version>, GLZ_THROW_OR_ABORT/GLZ_NOEXCEPT 宏 ...
   #if defined(__cpp_lib_expected) && __has_include(<expected>)
   #  include <expected>
   #else
   #  include <concepts> <deque> <exception> <functional> <memory>
   #  include <type_traits> <variant>
   namespace std { /* 完整 expected/unexpected 实现 */ }
   #endif
   ```

2. 源码 5 处 `#include <expected>` 统一改为 `#include <fex/expected_compat.hpp>`
   （filesystem.hpp / session.hpp / session.cpp / session_impl.hpp / passthrough.cpp）。
3. 标准名处理：**不**在配方写 `CMAKE_CXX_STANDARD=2b`；交回上游
   `set(CMAKE_CXX_STANDARD 23)`，CMake 对 clang-15 自动映射 `-std=c++2b`
   （flags.make 实证）。下游传播：`self.cpp_info.cxxflags = ["-std=c++2b"]`。
4. 依赖 liburing 时把 `pkg_check_modules(LIBURING ...)` 改为
   `find_package(liburing CONFIG REQUIRED)` + `liburing::liburing`
   （Conan CMakeDeps 生成目标；pkg-config 在 Conan 环境不可靠——liburing/2.15
   Conan 包不提供 .pc）。

## 验证（libfex/0.1.0）

| 门禁 | 结果 |
|---|---|
| polyfill 单头独立编译（c++2b + std::expected 用法模拟） | exit 0 |
| conan-verify G2 conan create 干净构建 | G1-G4 PASS，test_package ctest 1/1 Passed |
| 鸿蒙专项测试 `harmonyos_libfex_test` 实跑 | ALL PASSED，exit 0（SHA-256 e539e10d8b954a89972d18ff66f522ac4e6f5350c1cbf7dc5a34d869ce9ab2a7） |

### R02 返工修复与复验（PR #10426 代码审查）

| 项 | 修复 | 复验 |
|---|---|---|
| P1 | `expected<T,E>::operator=`（复制/移动）`has_val` 赋值移到状态分支之后 | 混合状态赋值（值→错/错→值）回归断言实测通过 |
| P2 | 移动构造 noexcept 第二操作数 `T`→`E` | static_assert 实测 |
| P2 | `or_else(F&&) const&&` void 版条件 `!has_value()`→`has_value()` | 值/错误态断言实测 |
| P3 | 转换移动构造 `const U&/G&`→`U&&/G&&` 右值转发 | move-only 类型实测可编译运行 |
| 测试 | 消费者与鸿蒙专项新增混合状态赋值、or_else 断言；harmonyos-test 加 `-UNDEBUG` 保证 Release 下断言真实执行 | 全部实跑通过 |

教训/注意：vendored 第三方单头（MIT）可能带上游 TODO 注释与实现缺陷，合入前须独立代码审查并补回归测试；new-file 补丁头必须为 `--- /dev/null`；CI 预下载步骤（predl）就地把 conandata 改写为 file:// 时不得提交污染版本。

## 适用边界 / 反例

- 适用：公共头直接暴露 `std::expected`（或其它缺失 C++23 头）的 C++23 库，
  在 OHOS clang-15/libc++15 工具链下适配；也适用任意 `<expected>` 缺失的
  clang15/libc++15 系列工具链。
- 反例：仅内部实现使用 std::expected、公共头不暴露的库，可采用
  glaze/8.3.0 的 glz 命名空间改名方案（更安全，无需注入 std 命名空间）。
- 注意：注入 namespace std 属务实兼容手段，须仅在 `__cpp_lib_expected`
  未定义时生效；polyfill 头必须随库一并安装（公共头引用了它），否则
  消费者编译再次失败。

## 查重差异

- 七轴：exact_duplicate=否；causal_duplicate=部分（E130 同为 libc++15 头缺口但
  方向相反——升标准 vs 补头）；trigger_overlap=部分（E130 是 nullptr_t/__abi_tag__，
  本候选是 expected）；solution_overlap=部分（glaze 用 glz 改名，本候选用
  namespace std 注入）；combination_novelty=是；boundary_novelty=是；
  test_migration_novelty=否。
- 关系：similar_to E130/E455/DRAFT-glaze；caused_by OHOS clang-15/libc++15
  工具链版本；conflicts_with 无。

## 决定

- `new_draft`（Path B 知识库扩展）：C1（expected polyfill）验证通过、可跨库
  复用、查重未命中且存在组合/边界新增差异；C2（c++2b/CMAKE_CXX_STANDARD 写法）
  与 C3（liburing find_package）作为边界细节并入本条草稿。