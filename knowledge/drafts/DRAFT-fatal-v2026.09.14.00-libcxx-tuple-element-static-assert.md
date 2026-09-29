# 新版 libc++ 的 std::tuple_element 越界 static_assert 击穿 SFINAE 完整性探测

> 状态：草稿（contributor SunShine_06）｜ 触发事件：fatal v2026.09.14.00 鸿蒙 PC 适配（PR #13207）
> 关联：与 `DRAFT-fatal-v2026.09.14.00-rope-std-iterator-deprecated` 同属「新版 libc++ 严格化」家族，
> 但机制不同——本条是 **static_assert 击穿 SFINAE**（替换失败变硬错误），彼条是**弃用属性被 -Werror 升级**

- **草稿 ID**: DRAFT-fatal-v2026.09.14.00-libcxx-tuple-element-static-assert
- **来源**: fatal/v2026.09.14.00（上游 tag v2026.09.14.00）鸿蒙 PC 适配实测
- **分类**: ohos, toolchain, libc, c++, compiler, compilation, testing
- **状态**: 已随 PR #13207 提交至 `knowledge/drafts/`，未分配 E 编号（待主编 `graph promote`）

## 问题 / 错误签名

- 编译 `fatal/type/test/deprecated_transform_test.cpp` 失败：

```
libcxx-ohos/include/c++/v1/__utility/pair.h:453:5: error: static assertion failed
    due to requirement '2UL < 2': Index out of bounds in std::tuple_element<std::pair<T1, T2>>
    static_assert(_Ip < 2, "Index out of bounds in std::tuple_element<std::pair<T1, T2>>");
./fatal/type/impl/is_complete.h:16:37: note: in instantiation of template class
    'std::tuple_element<2, std::pair<void, void>>' requested here
    template <typename T, std::size_t = sizeof(T)>
fatal/type/test/deprecated_transform_test.cpp:134:23: note: in instantiation of
    template type alias 'is_complete' requested here
    FATAL_EXPECT_FALSE((is_complete<std::tuple_element<2, pair>>::value));
```

- 复现（OHOS PC, clang 15.0.4 + libcxx-ohos）：
  `clang++ -Wall -Werror -Wextra -std=c++17 -I . fatal/type/test/deprecated_transform_test.cpp`

## 根因

1. 上游用「完整性探测」手法做断言：`is_complete<T>` 内部以 `sizeof(T)` 作为默认模板实参
   触发 SFINAE，期望越界/未定义的 `std::tuple_element<2, std::pair<...>>` 表现为
   **不完整类型**（替换失败 → 判 `false`）。
2. 新版 libc++（OHOS 用 libcxx-ohos, clang 15）在 `std::tuple_element` 特化内加入了
   `static_assert(_Ip < 2, "Index out of bounds ...")`（libstdc++ 同样如此）。
   **标准库的 `static_assert` 不处在 SFINAE 上下文**：一旦实例化该类模板即硬错误，
   不会被替换失败吞掉，于是上游断言从「编译期比较」变成「编译失败」。

## 最小修复方案

在 `archives/f/fatal/v2026.09.14.00/patches/0002-*.patch` 中：用实现宏守卫这一行断言，保留对
仍 SFINAE 友好实现的检查。

```cpp
#if !defined(_LIBCPP_VERSION)
  FATAL_EXPECT_FALSE((is_complete<std::tuple_element<2, pair>>::value));
#endif
```

要点：
- **只注释掉期望的那一行 `FATAL_EXPECT_*`，不删除 `FATAL_TEST` 用例本身**，
  用例计数保持不变（该 TU 仍 85 个用例，实测 85/85 通过），避免被判定为「减少测试」。
- 同类「用 SFINAE 探测标准库类型完整性」的写法在 `_LIBCPP_VERSION`/`__GLIBCXX__`
  存在时都应视为不可靠。

## 实际验证结果

- 打补丁前后对比（真机 HarmonyOS PC aarch64，2026-09-25）：
  - 补丁前：`deprecated_transform_test.cpp` 编译失败 → 该 TU 的 85 个用例 0 个执行。
  - 补丁后：编译成功，`85/85` 通过。
- 全量复跑：67/67 TU 编译成功，839/839 用例通过（0 失败 0 跳过）。

## 适用范围

- 在 OHOS（clang + libcxx-ohos）或任何使用「较新 libc++/libstdc++」的工具链上，
  构建以 SFINAE 探测标准库类型完整性（`sizeof` 探测、`is_complete` 类工具）的
  C++ 模板库或其测试。
- 典型受害者：`std::tuple_element`、`std::get`、`std::variant_alternative` 等
  带越界 `static_assert` 的类型。

## 非适用边界

- 不涉及该探测手法的库无需本方案。
- 不得用「注释掉整个 `FATAL_TEST` 用例」来绕过（会减少上游用例数 → 触发测试减少判定）。
- 不得关闭 `-Werror` 或整体降级标准来掩盖问题（上游 harness 参数须原样保留）。

## 查重差异

`draft-review` 预审实测（本仓库引擎，2026-09-25）：

```
质量预检: signature=✅  root_cause=✅  rec=✅
相似正式条目 TOP5:
  E440  score=0.15  (sig=0.2 kw=0.0 cat=0.2)
  E259  score=0.14  (sig=0.2 kw=0.0 cat=0.0)
  E353  score=0.10  (sig=0.14 kw=0.0 cat=0.0)
  E063  score=0.05  /  E130  score=0.04  ← libcxx-ohos 相关
📌 预审建议: create
```

- 判 **create**：TOP 相似条目（E440 0.15 / E259 0.14）与本草稿在正文上并非同类。
  **E440** 是 CMake 组件依赖在 OHOS 被跳过导致的 `Qt6::Help` 引用失败，**E259** 是
  `assert()` 包裹带副作用表达式（NDEBUG 下副作用消失），两者与「标准库模板硬化」无关，
  只是签名文本层面的偶然重叠（`static` / `assert` 词形）。
- **E130**（libcxx-ohos 的 `__abi_tag__` / C++ 标准版本，score 0.04）与本草稿共享
  「OHOS 自带 libcxx 与上游假设不一致」这一领域标签，但 E130 的对策是改 C++ 标准版本、
  现象发生在类型 ABI 层面；本条的机制是**标准库越界 `static_assert` 不处于 SFINAE 上下文**，
  对策是守住那一行探测、保持用例数不变——根因、复现、修法、禁例全不同，故建议并存。
- 与同批的 `DRAFT-fatal-v2026.09.14.00-rope-std-iterator-deprecated` 互为姊妹条目，已用 `similar_to` 显式互链。

## 关联交付

- 本草稿与 `archives/f/fatal/v2026.09.14.00/**`（含 `patches/0002-*.patch`、
  `conanfile.py` 的 `_run_upstream_tests()`、`reports/test-report.md`）属同一交付范围。
- 已随 PR #13207 提交（`knowledge/drafts/`）。主编 promote 命令：
  `python3 scripts/ohc-run.py graph promote fatal-v2026.09.14.00-libcxx-tuple-element-static-assert`
