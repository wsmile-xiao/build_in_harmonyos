# DRAFT — OHOS libc++（LLVM 15）span 不支持 string_view 范围构造，用 value_type*size 计算字节数

> 状态: 草稿（基于 itlib 1.12.2 R01 真实证据，四范围查重未命中 → 路径 B 候选）。
> 触发: itlib 1.12.2 R01（pc1-60，2026-09-27）。
> 查重: 正式知识 E397（typename 家族）、E351（abiword compat）、E321（header-only 配方）
> 均为部分覆盖，未命中「OHOS libc++ span 缺 string_view 范围构造」机制。

## 真实问题（场景）

itlib（header-only C++ 模板库集合）的 `include/itlib/opt_ref_buffer.hpp` 在
`make_span` 内用 C++20 写法 `std::span(container).size_bytes()` 计算字节数，
`container` 为 `std::string_view` / `std::wstring_view`（经 `ref(str)` 传入）。

OHOS SDK 的 libc++（LLVM 15）对该范围/CTAD 构造支持不完整，编译报错：

```
include/itlib/opt_ref_buffer.hpp:122:28: error: no matching conversion for
functional-style cast from 'std::string_view' to 'std::span<char>'
candidate constructor not viable: no known conversion from 'std::string_view'
to 'const std::span<char, 18446744073709551615>'
```

libstdc++ / 较新 libc++ 均支持该构造，因此是 OHOS 工具链特有的可移植性差异。

## 根因

C++20 `std::span` 的范围构造函数 `template<class R> span(R&&)` 在 OHOS libc++
（LLVM 15）对 `std::string_view` / `std::wstring_view` 不可用（候选集仅剩
拷贝构造）。任何对 string_view 类连续容器写 `std::span(container)` 的
C++20 代码在 OHOS 上都会触发同类首错。

## 修复方案

补丁将字节数计算改为不依赖 span 范围构造的等价式：

```cpp
-        const auto csize = std::span(container).size_bytes();
+        const auto csize = container.size() * sizeof(typename Container::value_type);
```

对 vector / string_view / wstring_view 等连续容器，二者结果一致；
后续 `reinterpret_cast` 与 `csize / sizeof(value_type)` 逻辑不变。
若需保留 span 对象，可改用 `std::span(container.data(), container.size())`
（data/size 双参构造在 LLVM 15 libc++ 可用）。

## 验证

- 补丁应用前：上游 `t-opt_ref_buffer-20.cpp` 编译报 2 个首错（string_view / wstring_view 转换失败）。
- 补丁应用后：上游测试构建 0 错误，53 个 CTest 注册项 52 通过；`conan create`
  （ohos-aarch64，clang 15.0.4）PASS，test_package 消费者 `./test_itlib` PASS。
- 日志：`reports/upstream-tests-build.log`（SHA-256 efda8dab580672646c54a5ded7bc8e5dfdca132f11b7f8348855941532caeb7e）、
  `reports/conan-create.log`。

## 适用边界

- **适用**：OHOS libc++（LLVM 15）上任何对 string_view 类连续容器做
  `std::span(container)` CTAD 的 C++20 代码（任一 C++20 库源码/测试）。
- **反例**：libstdc++ / 较新 libc++（含完整范围构造）无需该改写；
  需要传递 span 对象本体而非仅取字节数时，应改用 data()/size() 双参构造。

## 关系

- similar_to: E397（同属 OHOS clang/libc++ 可移植性家族，但 E397 是 typename elision，本条是 span 范围构造）
- caused_by: 无
- prerequisite_of: 无
- conflicts_with: 无
