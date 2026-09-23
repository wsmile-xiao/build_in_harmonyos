# DRAFT: OHOS SDK libc++ 缺少 C++20 ranges 算法重载

## 现象

上游使用 `std::ranges::none_of(range, pred)`（C++20 ranges 算法）的源码，
在 OHOS SDK 工具链（clang 15 + 配套 libc++）下以 `-std=c++20` 编译失败：

```
error: no member named 'none_of' in namespace 'std::__n1::ranges'; did you mean 'std::none_of'?
note: 'std::none_of' declared here
```

前一阶段（cppstd=17 时）的报错形态是误导性的 `invalid argument type 'void'
to unary expression`（lambda 返回 void 传导到 remove_if 谓词），实际根因相同。

## 根因

OHOS SDK 的 libc++ 是裁剪版：`<algorithm>` 只含 C++17 迭代器对版本
`none_of(first, last, pred)`，未随 C++20 添加 ranges 命名空间重载
`none_of(range, pred)`。KDE Frameworks 6.28+ 源码已全面使用 ranges 版。

## 修复

可移植性补丁：`std::ranges::none_of(range, pred)` →
`std::none_of(range.cbegin(), range.cend(), pred)`（语义完全等价）。

实证：kholidays 6.28.0 `src/holidayregion.cpp` 单点替换后，上游 7 个
autotests（含 testholidayregion 对 filterCategories 路径的覆盖）全过，
CI 构建 #51068 passed。

## 适用面

所有 OHOS 适配中用到 C++20 ranges 算法的包。同类可替换：
`all_of/any_of/find_if/count_if/for_each` 的 ranges 版本若报同款
"no member named 'X' in namespace 'std::ranges'"，均可用迭代器对版本替换。

## 预扫描建议

`std::ranges::(none_of|all_of|any_of|find_if|count_if)` 出现即预警。
