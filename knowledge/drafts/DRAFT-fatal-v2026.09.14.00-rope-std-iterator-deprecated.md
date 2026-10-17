# std::iterator C++17 弃用（libc++ 标 deprecated）打断 header-only 库的 -Werror 构建

> 状态：草稿（contributor SunShine_06）｜ 触发事件：fatal v2026.09.14.00 鸿蒙 PC 适配（PR #13207）
> 关联：与 `DRAFT-fatal-v2026.09.14.00-libcxx-tuple-element-static-assert` 同属「新版 libc++ 严格化」家族，
> 但机制不同——本条是**弃用属性被 -Werror 升级为硬错误**，彼条是 **static_assert 击穿 SFINAE**

- **草稿 ID**: DRAFT-fatal-v2026.09.14.00-rope-std-iterator-deprecated
- **来源**: fatal/v2026.09.14.00（上游 tag v2026.09.14.00）鸿蒙 PC 适配实测
- **分类**: ohos, toolchain, libc, c++, compiler, warnings, headers, compilation
- **状态**: 已随 PR #13207 提交至 `knowledge/drafts/`，未分配 E 编号（待主编 `graph promote`）

## 问题 / 错误签名

- 编译 `fatal/string/test/rope_test.cpp`（间接包含 `fatal/string/rope.h`）失败：

```
fatal/string/rope.h:648:17: error: 'iterator<std::bidirectional_iterator_tag, char>'
    is deprecated [-Werror,-Wdeprecated-declarations]
    public std::iterator<
                ^
libcxx-ohos/include/c++/v1/__iterator/iterator.h:24:29: note:
    'iterator<std::bidirectional_iterator_tag, char>' has been explicitly marked deprecated here
struct _LIBCPP_TEMPLATE_VIS _LIBCPP_DEPRECATED_IN_CXX17 iterator
```

- 复现（OHOS PC, clang 15.0.4 + libcxx-ohos）：
  `clang++ -Wall -Werror -Wextra -std=c++17 -I . fatal/string/test/rope_test.cpp`

## 根因

1. `std::iterator` 自 **C++17 起弃用**（C++20 移除）。libc++ 对其展开为
   `_LIBCPP_DEPRECATED_IN_CXX17` → `__attribute__((deprecated))`。
2. 上游 harness 使用 `-Wall -Werror -Wextra`，告警被升级为硬错误，整个 TU 无法编译
   （fatal 的 `rope_test.cpp` 共 47 个用例因此一个都跑不了）。
3. 关键影响面：`rope.h` 是**安装头文件**，不只影响测试——任何消费者项目以
   `-Werror` 使用 `fatal/string/rope.h` 都会失败。

## 最小修复方案

在 `archives/f/fatal/v2026.09.14.00/patches/0001-*.patch` 中：移除 `std::iterator` 基类，改为
**语义等价的**显式成员 typedef。

```cpp
  struct const_iterator {
    using iterator_category = std::bidirectional_iterator_tag;
    using value_type = rope::value_type;
    using difference_type = rope::difference_type;
    using pointer = rope::value_type *;
    using reference = rope::value_type &;
```

要点：
- `std::iterator<Category, T, Distance, Pointer = T*, Reference = T&>` 等价于上述 5 个
  typedef；消费者经 `std::iterator_traits` 读取的契约完全不变。
- 类内自引用需限定为 `rope::value_type`（避免 `using value_type = value_type` 自引用）。
- 不要改用「加 `-Wno-deprecated-declarations`」的绕法：那会同时掩盖消费者侧问题。

## 实际验证结果

- 补丁前：`rope_test.cpp` 编译失败 → 该 TU 的 47 个用例 0 个执行。
- 补丁后：编译成功，`47/47` 通过。
- 消费者侧复验（`test_package/rope_iterator_test.cpp`）：在 `-Werror -Wextra` 下编译通过，
  并用 `std::iterator_traits<const_iterator>::iterator_category` 与 5 个 typedef 的
  `static_assert` 校验契约完整；运行期遍历 `fatal::rope<>` 得到
  `walked 'hello, world!' (13 chars, std::distance=13)`。
- 全量复跑：67/67 TU 编译成功，839/839 用例通过（0 失败 0 跳过）。

## 适用范围

- 在 OHOS（clang + libcxx-ohos）或任何 C++17 及以上、以 `-Werror` 构建的工程中，
  使用 `std::iterator` 作为自定义迭代器基类的**安装头文件**或上游测试 TU。
- 典型受害者：老一代 C++ 库（2016 前后）的迭代器实现，如 fatal 的
  `fatal/string/rope.h`、`fatal/type/deprecated/*`。

## 非适用边界

- 已经自行定义 5 个成员 typedef 的迭代器无需本方案。
- 若类模板本身还依赖 `std::iterator` 的其它行为（实际上它只有 typedef），需逐项核对后再改。
- 不得放宽 `-Werror` 或整体降级 C++ 标准版本（会与上游 harness 参数不一致）。

## 查重差异

`draft-review` 预审实测（本仓库引擎，2026-09-25）：

```
质量预检: signature=✅  root_cause=✅  rec=✅
相似正式条目 TOP5:
  E198  score=0.14  (sig=0.2 kw=0.0 cat=0.0)   ← 最近邻
  E063  score=0.05  (sig=0.0 kw=0.05 cat=0.14)
  E169 / E462 / E217  score=0.04
📌 预审建议: create
```

- 判 **create**：无高相似条目。最近的 **E198**（score 0.14）同属「编译告警被 `-Werror`
  升级为硬错误」家族，但 E198 的载体是**上游源码自身**的 `-Wdeprecated-copy`（自定义 `operator=`
  导致隐式拷贝构造被弃用），本条的载体是**标准库** `std::iterator` 基类被 libc++ 标注弃用；
  两者触发条件、修法（改源码 vs. 展开等价 typedef）、影响面（单个 TU vs. 安装头文件全部消费者）均不同。
- **E063**（`-Werror` 语义族，score 0.05）只描述「启用 -Werror 会把告警变错误」这一大前提，
  不涉及 `std::iterator` 这一具体 API 的弃用与等价替换写法。
- 与同批的 `DRAFT-fatal-v2026.09.14.00-libcxx-tuple-element-static-assert` 互为姊妹条目
  （同一交付、同一「新版 libc++ 严格化」根因族，但机制与修法完全不同），已用 `similar_to` 显式互链。

## 关联交付

- 本草稿与 `archives/f/fatal/v2026.09.14.00/**`（含 `patches/0001-*.patch`、
  `test_package/rope_iterator_test.cpp`、`reports/test-report.md`）属同一交付范围。
- 已随 PR #13207 提交（`knowledge/drafts/`）。主编 promote 命令：
  `python3 scripts/ohc-run.py graph promote fatal-v2026.09.14.00-rope-std-iterator-deprecated`
