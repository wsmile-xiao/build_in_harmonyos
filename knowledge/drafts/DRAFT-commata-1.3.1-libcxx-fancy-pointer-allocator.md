# DRAFT-commata-1.3.1-libcxx-fancy-pointer-allocator

## 问题
OHOS（libc++）上，`std::basic_string<wchar_t, …, tracking_allocator<fancy_allocator<wchar_t>>>` 编译失败：
`call to implicitly-deleted default constructor of 'std::basic_string<...>::__rep'`。

## 根因
libc++ 的 `std::basic_string` 使用 SSO 布局，内部 `__rep` 为含 `__long`/`__short` 变体的 union 且无用户提供的默认构造。
当分配器 `pointer` 类型为 `fancy_ptr`（用户自定义指针，非平凡默认构造）时，union 变体 `__long` 的非平凡默认构造使
`__rep` 默认构造被隐式删除，任何需要默认构造 `__rep` 的构造路径（如 `basic_string(const CharT*, alloc)`）编译失败。
libstdc++/MSVC 实现不依赖该 union 布局，可正常编译，故上游 CI（libstdc++）不暴露。

## 触发条件
- 编译器：OHOS clang 15 + libcxx-ohos（`_LIBCPP_VERSION` 定义）
- 代码：用自定义 fancy-pointer 分配器构造 `std::basic_string`（典型：分配器传播测试）

## 方案
测试/示例代码条件编译：
```cpp
#if defined(_LIBCPP_VERSION)
    tracking_allocator<std::allocator<wchar_t>> alloc(total); // 保留分配器传播验证
#else
    tracking_allocator<fancy_allocator<wchar_t>> alloc(total);
#endif
```

## 验证
- 修复前：`TestRecordExtractor.cpp` Fancy 用例编译失败（2 errors，compressed_pair.h/string.h）
- 修复后：commata 上游测试全量 `668/668 PASSED`（含 Fancy 用例，total > 0 断言仍生效）

## 适用边界
- 仅影响 libc++（OHOS）；libstdc++/MSVC 下 fancy pointer 分配器可用
- 属平台工具链限制，不是被测库功能缺陷

## 反例与限制
- 不得改用 `-stdlib=libstdc++`（OHOS clang 拒绝）
- 不得删除 Fancy 用例断言以"通过"——保留 `ASSERT_GT(total, 0U)` 证明分配器传播
