# DRAFT: OHOS libc++(clang15) 缺 ranges 算法的投影/双 range 形式改写

> 既有草稿 `DRAFT-E5xx-ohos-libcpp-missing-ranges-algorithms`（kholidays 6.28.0）覆盖
> 简单形式（range, pred）→（begin, end, pred）的机械替换。本草稿记录**补集**：
> 投影式 find 与双 range swap_ranges 两种不能被机械替换的形式（ctd_cli 0.1.3 实证）。

## 现象

```
src/Parse.cpp:42: error: no member named 'find' in namespace 'std::ranges'
    std::ranges::find(subElementsInterfacesSpans.namedArguments, argumentName,
                       [](auto &byInterface) { return byInterface->getLongFlag(); });
Function.h:141: error: no matching function for call to 'swap_ranges'
    std::ranges::swap_ranges(other.memory, memory);
```

## 根因

OHOS SDK 的 libc++ 是 LLVM 15 裁剪版，`<algorithm>` 只有 C++17 迭代器对版本，
C++20 ranges 算法族（find/for_each/swap_ranges/construct_at 等）在 LLVM 16 才随 libc++ 提供。
简单的 `ranges::X(range, args...) → std::X(begin, end, args...)` 替换对
两参数/多参数简单形式成立，但对**带投影的 find**（第三个参数是 proj，std::find 不接受）
与**双 range 的 swap_ranges**（std::swap_ranges 是三迭代器签名）会继续报错。

## 修复（可移植性改写，无平台宏）

1. 投影式 find → find_if + lambda（投影结果与目标值比较，捕获值）：
```cpp
// 改前
std::ranges::find(subcommands, nextArg, [](auto *e){ return e->getName(); });
// 改后
std::find_if(subcommands.begin(), subcommands.end(),
             [&](auto *e){ return e->getName() == nextArg; });
```
2. 双 range swap_ranges → 三迭代器：
```cpp
std::ranges::swap_ranges(a, b)  →  std::swap_ranges(std::begin(a), std::end(a), std::begin(b));
```
3. construct_at / destroy_at → std::construct_at / std::destroy_at（libc++15 已提供）。
4. 简单形式（find/find_if/find_if_not/any_of/all_of/for_each/sort/adjacent_find/copy/fill）
   按 DRAFT-E5xx 机械替换为迭代器对版本即可。

## 验证

ctd_cli 0.1.3：35 处 ranges 调用经 7 个补丁改写后，库编译通过；
上游 16/16 GoogleTest 用例（command_line_interface_test 11 + cli_status_test 4 +
function_test 1）全部运行通过；conan create（ohos-aarch64 / clang-15 / libc++）G2 PASS，
test_package 消费者测试与鸿蒙专项测试 2/2 通过。

## 适用边界

- 适用：目标 libc++ < 16（OHOS SDK clang15）且使用 ranges 算法的任意 C++20 三方库。
- 反例/不适用：libc++ ≥ 16、libstdc++ ≥ 12（GCC 12+）无需改写；
  `std::views::*` 视图管道不在本文范围（需降级为循环或中间容器）；
  深拷贝语义（swap_ranges 涉及的两个 range 等长）在改写时须保持原语义。

## 查重关系

- similar_to: DRAFT-E5xx-ohos-libcpp-missing-ranges-algorithms（简单形式替换的补集）、
  DRAFT-332-openrct2-0.5.3-libcpp15-cpp20-compat（libc++15 C++20 兼容清单的另一部分）
- 与正式条目 E092（CMake 不认识 OHOS 平台）、E130/E455（libcxx 配置）无重叠。