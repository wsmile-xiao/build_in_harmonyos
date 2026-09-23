# OHOS clang 15 / libc++ 15 的 C++20 能力缺口（草稿）

- **来源**：cdo 2.6.3 适配（archives/c/cdo/2.6.3/notes.md）
- **日期**：2026-09-12
- **适用范围**：所有在 OHOS clang 15 + libc++ 15.0.4 上构建、使用 C++20 ranges 或结构化绑定捕获的 C/C++ 项目

## 条目要素（对应路径 B 场景一的「使用说明 / 适用范围 / 输入输出定义 / 示例」）

- **使用说明**：见下方「现象 → 根因 → 解决办法」，含可直接复制的补丁/配方片段
- **适用范围**：见本文件开头的「适用范围」与 kv 的 `affected_scope`
- **输入输出定义**：
  - 输入（触发条件）：kv 的 `error_signature`（报错特征） + `trigger_tool` / `phase`
  - 输出（验证方式）：kv 的 `verification_cmd` + 本文件「验证」一节的实测结果
- **示例**：本文件中的补丁片段、探针命令与 conan 命令

## 现象

1. 上游头文件里的 ranges 判定直接失败：

```
src/cpp_lib.h:17:2: error: C++20 Ranges library is Not Available!
```

2. 不加任何开关时，C++20 代码里 `std::ranges::sort` 等根本不存在：

```
error: no type named 'sort' in namespace 'std::ranges'
error: no member named 'fill' in namespace 'std::ranges'
```

3. 打开实验特性后，lambda 捕获结构化绑定仍失败：

```
src/operators/Diff.cc:487:84: error: 'levelID' in capture list does not name a variable
```

## 根因

- libc++ 15 的 `__config` 对未开启实验特性的使用者定义 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES`：
  `#if !defined(_LIBCPP_ENABLE_EXPERIMENTAL) && !defined(_LIBCPP_BUILDING_LIBRARY)`；
- 即使开启，`__cpp_lib_ranges` 也只有 **201811L**，低于标准 C++20 的 **202110L**——按
  `>= 201911L` 判定的上游头文件仍会 `#error`；
- `std::views::split` / `std::views::zip` 在实验模式下仍缺失（通常由
  `__cpp_lib_ranges_zip` 守卫，上游多已备手写分支）；
- clang 15 未实现 P1091R3：结构化绑定不能被 lambda 捕获（clang 17 才支持）。

## 解决办法（推荐路径）

1. recipe 的 CXXFLAGS 追加 `-D_LIBCPP_ENABLE_EXPERIMENTAL`；
2. 把上游 `#if __cpp_lib_ranges >= 201911L` 改为 `#if defined(__cpp_lib_ranges)`（标准特性宏，非平台宏）；
3. 结构化绑定位置先拷贝成普通局部变量再捕获。

## 验证

- `conan create . -pr:h=ohos-aarch64-wsl -pr:b=default`（cdo/2.6.3，2026-09-12）configure 通过、生成 aarch64 ELF；
- 探针：`-std=gnu++20 -D_LIBCPP_ENABLE_EXPERIMENTAL` 下 `std::ranges::sort/fill/fill_n/transform/is_sorted/count_if/minmax_element/max/find/copy_n/any_of` 与
  `range_value_t/range_reference_t/input_range/random_access_range` 全部编译通过；
  `std::views::split`/`zip` 仍不可用（走上游手写分支）。

## 相关

- **预审相似条目**：E292（大型 C++ 数据处理库的 C++20 标准库能力边界，相似度 0.33，灰区——本条聚焦 clang15/libc++15 的 ranges 开关与 P1091R3，与之互补不重叠）

- cdo 补丁：`patches/0002-cpp-lib-incomplete-ranges.patch`、`0004/0005-*-lambda-structured-binding.patch`
- 同类 libc++ 缺口记录：`DRAFT-6487-classads-libcxx-missing-string-out-instantiation.kv`
