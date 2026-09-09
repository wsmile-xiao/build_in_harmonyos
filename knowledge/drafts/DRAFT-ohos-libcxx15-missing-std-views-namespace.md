# E-entry 草稿文档 — OHOS clang15/libc++15 不提供 std::views 视图命名空间

配套: `DRAFT-ohos-libcxx15-missing-std-views-namespace.kv`
触发任务: boost-ext-ut 2.3.1（PR #8569，archives/b/boost-ext-ut/2.3.1，patch 0001）
同族条目: DRAFT-ohos-libcxx15-format-ranges-capability-gap（<format> stub/ranges 内存算法）、
DRAFT-ohos-libcxx15-missing-cpp20-ranges-algorithms（std::ranges 算法重载）——本条补
std::views 视图适配器与判据反例，三者合起来构成 OHOS libc++15 C++20 ranges 缺口全图。

## 症状（稳定错误签名）

```
example/parameterized.cpp:50:12: error: no member named 'views' in namespace 'std'
   50:   } | std::views::iota(1, 4);
```

## 根因

OHOS SDK26 clang 15.0.4 配套 libc++（LLVM 15）定义 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES`
（ranges 实现不完整），不提供 `std::views` 视图命名空间（`std::views::iota` 等不可用）。

**反直觉点（本条核心增量）：特性测试宏 `__cpp_lib_ranges` 却已定义——版本宏 ≠ 可用性。**
以 `__cpp_lib_ranges` 或 `__has_include(<ranges>)` 作条件编译判据在 OHOS 上必然漏判。
探针三连（实机）：

```bash
# 探针 1: 缺口宏已定义
$ printf '#include <version>\n#if defined(_LIBCPP_HAS_NO_INCOMPLETE_RANGES)\nHAS_GAP\n#endif' \
  | clang++ -std=c++20 -stdlib=libc++ -E - | tail -1
HAS_GAP
# 探针 2: std::views 不可用
$ printf '#include <ranges>\nint main(){ auto r = std::views::iota(1,4); }' \
  | clang++ -std=c++20 -stdlib=libc++ -fsyntax-only -
error: no member named 'views' in namespace 'std'
```

注意上游项目常用平台宏守卫此类代码（boost-ext-ut 上游用 `__EMSCRIPTEN__` 守卫同一处
`"views"_test`），OHOS 恰好命中"上游守卫未覆盖的平台"。

## 方案

条件编译改用 libc++ 自身缺口宏，并与上游已有平台守卫合并到同一 `#if`：

```diff
-#ifndef __EMSCRIPTEN__
+#if !defined(__EMSCRIPTEN__) && !defined(_LIBCPP_HAS_NO_INCOMPLETE_RANGES)
```

不引入 `__OHOS__` 等平台宏（R8/PF5 合规）；libc++ 17+ ranges 补齐后宏不再定义，被守卫
代码自动恢复。补丁验证：`git apply --check` 通过；修复后 41 个 example 全部编译、
ctest 4/4（PR #8569 归档实测）。

## 定位方法（效率要点）

不要等全量构建失败逐个修：

```bash
for f in $(find . -name '*.cpp'); do
  clang++ -std=c++20 -stdlib=libc++ -fsyntax-only -Iinclude $f || echo "HIT $f"
done
```

本轮 45 个上游测试/示例文件 30 秒定位出唯一受影响文件。

## 禁忌

- 禁止用 `__cpp_lib_ranges` 守卫（OHOS 上已定义，漏判）。
- 禁止降级 `-std=c++17` 掩盖（改变语义、掩盖 C++20 依赖）。

## 适用范围 / 解除条件

- 适用：任何 C++20 源码使用 `std::views` 视图适配器的库在 OHOS clang15/libc++15 下。
- 解除条件：OHOS SDK 升级到 libc++ ≥ 17 后 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES` 不再
  定义，守卫自动失效。
