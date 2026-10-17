# DRAFT-flatbush-1.5.0-header-only-cxx-standard-macro-cpp-info-defines — header-only INTERFACE 库的 C++ 标准门控宏必须经 cpp_info.defines 传播

## 问题现象

flatbush 1.5.0（chusitoo/flatbush，packed Hilbert R-tree 空间索引的 C++ 移植，
header-only INTERFACE target）在 OHOS armv8 上做 Conan 2.x 适配时，按普通
header-only 配方打包后，用 C++17 直接编译已安装的头文件报错：

```
reports/ohos-test.cpp:14:2: error: "flatbush package must propagate FLATBUSH_SPAN ..."
#error "flatbush package must propagate FLATBUSH_SPAN for OHOS C++17 consumers"
.../include/flatbush.h:1123:3: error: no template named 'span'
  span<Box<ArrayType>> mBoxes;
   ^
.../include/flatbush.h:1153:31: error: no template named 'span'
Flatbush<ArrayType>::Flatbush(span<const uint8_t> iBytes) ...
15 errors generated.
```

## 根因分析

header-only 库为兼容低 C++ 标准，把"用自带 span 还是 std::span"做成编译宏门控：

```cpp
#ifndef FLATBUSH_SPAN
#include <span>         // 需要 cxx_std_20
using std::span;
#else
class span { ... };     // 自带实现，C++11/17 可用
#endif
```

上游 CMake 用 `option(WITH_SPAN ON)` + `target_compile_definitions(... INTERFACE
FLATBUSH_SPAN)` 把宏挂到 INTERFACE target 上。但这只对"走上游 CMake 目标"的
消费者生效。**Conan 打包后宏不会自动进包**——配方若不显式
`self.cpp_info.defines = ["FLATBUSH_SPAN"]`，CMakeDeps 生成的 config 就没有该宏，
C++17（OHOS profile `cppstd=17`）消费方编译 flatbush.h 走 std::span 分支 → 报错。

## 方案

header-only 配方的 `package_info()` 中，把上游 INTERFACE 宏显式写入
`self.cpp_info.defines`，与上游 `WITH_SPAN=ON` 默认一致（本库默认 ON → C++11
兼容），OHOS cppstd=17 消费方直接可用：

```python
def package_info(self):
    self.cpp_info.set_property("cmake_file_name", "flatbush")
    self.cpp_info.set_property("cmake_target_name", "flatbush::flatbush")
    self.cpp_info.defines = ["FLATBUSH_SPAN"]   # 与上游 WITH_SPAN=ON 默认一致
    self.cpp_info.includedirs = ["include"]
    self.cpp_info.bindirs = []
    self.cpp_info.libdirs = []
```

## 验证（flatbush 1.5.0 本轮真实日志）

1. 失败路径实测：不传宏时 `clang++ -std=c++17` 编译 → `no template named 'span'`
   （15 errors）；传 `-DFLATBUSH_SPAN` 后通过。
2. 鸿蒙专项测试 `reports/ohos-test.cpp`（`-std=c++17 -DFLATBUSH_SPAN -I <conan
   已安装 include>`）运行 exit 0：
   `PASS: OHOS C++17/FLATBUSH_SPAN + JS-compatible roundtrip ok`
3. `conan create`（ohos-aarch64 profile）G2 PASS；test_package L1 消费者 exit 0。
4. 日志：`archives/f/flatbush/1.5.0/reports/ohos-test-run.log`

## 适用边界 / 反例

- 适用：header-only / INTERFACE 库，头文件用编译宏门控 C++ 标准特性（自带
  span/optional/variant 等），目标平台 profile cppstd 低于宏关闭分支要求的标准。
- 边界：若库上游默认 `WITH_SPAN=OFF`（要求 cxx_std_20）且 OHOS profile 允许
  cppstd=20，则可不传宏、由消费方自行提供 C++20；本库上游默认 ON 故传宏。
- 反例：编译型（非 INTERFACE）库无此问题——宏走编译产物，不靠配方传播。

## 查重（七轴）

| 轴 | 结果 |
|----|------|
| exact_duplicate | false |
| causal_duplicate | false（E321 根因是 Conan 1→2 迁移，非宏传播） |
| trigger_overlap | partial（与 E321/E322 同 header-only+conan 触发面） |
| solution_overlap | partial（E321/E322 讲 cmake_file_name/target_name，未覆盖 defines 传播标准门控宏） |
| combination_novelty | true（宏门控 C++ 标准分支 + cpp_info.defines 传播 = 新增差异） |
| boundary_novelty | true（边界：上游默认宏 ON 时消费方无需 C++20；配方漏宏 → cppstd=17 直接编译失败） |
| test_migration_novelty | false |

similar_to: E321, E322, E257, E293；caused_by/prerequisite_of/conflicts_with: 无
