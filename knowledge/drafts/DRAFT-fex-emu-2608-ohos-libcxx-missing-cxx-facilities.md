# DRAFT-fex-emu-2608-ohos-libcxx-missing-cxx-facilities：OHOS libc++ 15 缺失 C++17 pmr / C++20 atomic_ref / ranges 算法——按「设施缺口」补 shim

> Contributor: Hawkninja21 | Status: Draft | Updated: 2026-09-30
> Source: FEX-Emu 2608 适配 HarmonyOS PC（路径C 高难度挑战，分支 feat/fex-emu-2608）
> 对应：`knowledge/drafts/DRAFT-fex-emu-2608-ohos-libcxx-missing-cxx-facilities.kv`

## 现象

把"Linux 上正常"的 C++20 项目（此处是 x86→AArch64 用户态重编译器 FEX-Emu）用 OHOS clang 15 编译，
第一批错误集中出现在三类现代设施上：

```text
FEXCore/include/FEXCore/fextl/memory_resource.h:9:10: fatal error: 'memory_resource' file not found
FEXCore/include/FEXCore/Utils/SpinWaitLock.h:134:27: error: no member named 'atomic_ref' in namespace 'std'
FEXCore/Source/Interface/Context/Context.h:317:27: error: no member named 'any_of' in namespace 'std::ranges'
```

三类成因**性质不同**，必须先定性再动手：

| 类别 | 定性 | 判据 |
|------|------|------|
| `std::pmr`（C++17） | **头被裁剪** | `ls c++/v1/ \| grep memory_resource` 无结果；`<experimental/memory_resource>` 只有声明，链接期 `undefined symbol` |
| `std::atomic_ref`（C++20） | **头被裁剪** | `__atomic/atomic_ref.h` 不存在；`<atomic>` 内无该符号 |
| `std::ranges` 算法 | **开关被关** | `__config:256` 在未定义 `_LIBCPP_ENABLE_EXPERIMENTAL` 时定义 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES` |

```cpp
// $SDK/.../c++/v1/__config (libcxx-ohos, _LIBCPP_VERSION 15004)
#  if !defined(_LIBCPP_ENABLE_EXPERIMENTAL) && !defined(_LIBCPP_BUILDING_LIBRARY)
#    define _LIBCPP_HAS_NO_INCOMPLETE_FORMAT
#    define _LIBCPP_HAS_NO_INCOMPLETE_RANGES
#  endif
```

**迷惑点**：三条错误看起来"同一类缺设施"，但处置完全不同——
ranges 只需一个编译宏，另外两个必须补实现。若一律"补宏"会卡住，若一律"换库"会引入 ABI 风险。

## 根因

1. **裁剪**：OHOS 的 libc++ 是精简打包。`<memory_resource>` 整份不存在，连带
   `std::pmr` 命名空间、`polymorphic_allocator`、以及**容器头里的 pmr 别名**
   （`std::pmr::map/list/vector/string`）都没有。因此即使你自带一份
   `memory_resource` 实现，容器别名也得自己补。
2. **开关**：libc++ 15 把 ranges 算法标记为 "incomplete" 并按需开关；上游 FEX CI
   用的 libc++ ≥16 已默认开启，所以上游从未暴露这个组合。
3. **语义差（更隐蔽的一类）**：`std::function` 的转换构造在 libc++ 15 上是
   **无条件非 noexcept**，而 FEX 的 `fextl::move_only_function` 依赖
   `noexcept(internal = std::move(f))` 作为"不分配"的编译期证明：

   ```cpp
   static_assert(noexcept(internal = std::move(wrapped_lambda)), "...");
   ```

   在 libc++ 15 上这条断言恒假；把它删掉后测试改成"检查实际分配次数"又暴露
   `AllocCount == 0` 失败——因为所有 callable 都落进了"外部存储 + 包装 lambda"
   分支，**每次构造都多一次分配**。这不是编译问题，是性能契约被破坏。

## 处置（三层：开关 / 补设施 / 恢复语义）

### ① ranges：一个宏 + 只对目标平台生效

```cmake
if (CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
  add_compile_definitions(_LIBCPP_ENABLE_EXPERIMENTAL)
endif()
```

### ② atomic_ref：自带 shim 头，`#if !defined(__cpp_lib_atomic_ref)` 守卫

以 clang `__atomic_*` builtin 实现 `load/store/exchange/fetch_add/fetch_sub/fetch_and/
fetch_or/fetch_xor/compare_exchange_weak|strong` 及复合赋值运算符。
关键验证：**128 位 CAS**（`std::atomic_ref<__uint128_t>`，FEX 用于
`compare_exchange_strong` 做 CMPXCHG16B 语义）实测被 clang 内联为
`ldaxp/stxp`，链接期不需要 `libatomic`：

```text
$ readelf -d probe | grep NEEDED
 0x0000000000000001 (NEEDED)  Shared library: [libc++_shared.so]
 0x0000000000000001 (NEEDED)  Shared library: [libc.so]
```

### ③ pmr：自带 shim 头 + `__has_include` 守卫

- `memory_resource`（抽象基类 + `do_allocate/do_deallocate/do_is_equal`）
- `polymorphic_allocator<T>`：**必须实现 uses-allocator 构造**，否则
  `pma->new_object<std::pmr::map<...>>()` 构造出来的容器拿不到 resource
  （FEX 的 `LookupCache` 正是这样用）；
- 容器别名 `std::pmr::{vector,list,set,map,unordered_map,basic_string,string,...}`；
- `new_delete_resource / get_default_resource / set_default_resource`。

### ④ 恢复 `std::function` 的"小对象不分配"语义

不要只把 `static_assert` 注释掉——那会静默破坏契约。按 libc++ 的内联缓冲定义
补一条等价判据，让分支选择与 libc++ ≥16 一致：

```cpp
// __functional/function.h: aligned_storage<3 * sizeof(void*)>::type __buf_;
template<typename F>
static constexpr bool FitsStdFunctionInlineBuffer() {
#if defined(_LIBCPP_VERSION)
  using Functor = std::remove_reference_t<F>;
  return sizeof(Functor) <= 3 * sizeof(void*) && alignof(Functor) <= alignof(void*);
#else
  return false;
#endif
}
```

同时把包装 lambda 的调用从 `(*moved_lambda)(args...)` 改为
`std::invoke(*moved_lambda, args...)`，这样"成员函数指针"这类 callable 在
包装分支里也能正确调用（libc++ 15 下它们会因分支差异落进包装分支）。

## 证据

| 项 | 结果 |
|---|---|
| `std::ranges` 探针 | 加宏前失败，加宏后 `any_of` 编译并通过运行 |
| `std::atomic_ref` 探针（含 `__uint128_t`） | 编译/链接/运行通过，无 libatomic |
| pmr shim 探针 | `std::pmr::{list,map,string,vector}` + `polymorphic_allocator<std::byte>` 通过 |
| 上游 `unittests/APITests/fextl_function` | 修复前 `AllocCount 4 != 0`；补内联判据后 **58 断言全过** |
| 全量编译 | `conan create` rc=0 |

## 铁律

- ❌ 不得 `-stdlib=libstdc++` 或混用两套 C++ 运行库（本环境只有 OHOS libc++）。
- ❌ 不得把 pmr 直接替换成 `malloc`、把 `atomic_ref` 降级成裸读写——那会丢内存序
  与 arena 批量释放语义，重编译器正确性不成立。
- ❌ 不得只删 `static_assert` 了事（会静默引入每次构造一次分配的回归）。
