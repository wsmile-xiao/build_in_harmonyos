# DRAFT-stdformat-to-fmt-substitution-downstream-effects — 替换 `std::format` 为 `fmt::format` 后必须同步处理的两处链接侧影响

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-11
> **Severity**: 🟡 medium | **Category**: linking / cmake / libcxx / format

## 相关既有条目（同族差异化定位）

| 既有条目 | 同族点 | 本 skill 的增量（差异化） |
|---------|--------|--------------------------|
| **DRAFT-enchantum-0.4.0-libcxx-ohos-format-stub** | 同属 OHOS `<format>` 占位头问题 | 那条讲**前提**：头存在但功能未实现（`__has_include` 误判）。本条目从该前提**继续**，讲"决定改用 fmt 之后"踩到的两处链接侧问题——是**下一步**，不是重复 |
| **E247** | 均为 `undefined symbol` 类链接失败 | E247 是 **pkg-config `Libs.private` 漏 C++ 运行时**（C 链接器场景）；本条目是 **CMake PRIVATE 不传播 + fmt 主版本 inline namespace**，成因与判别方式均不同 |
| **E473** | 均为 CMake target/链接传播问题 | E473 讲 CMakeDeps 只暴露部分 target（`WebP::webpdemux` 缺失）；本条目讲**替换引入的新依赖**未补链、以及**版本命名空间**不匹配 |

> 查证（2026-09-11）：`fmt::v7`、`fmt::v8`、`FMT_VERSION` 在 knowledge/doc 与
> knowledge/drafts 下命中 **各 0 条**；本条目为空白领域。

## Scope（何时用）

OHOS 上因 libc++15 的 `<format>` 不可用（见 enchantum 那条），把上游的 `std::format` 机械替换为 `fmt::format` 时。**替换本身只是文本操作，但它引入两处链接侧问题**：

```
ld.lld: error: undefined symbol: fmt::v7::detail::vformat(fmt::v7::basic_string_view<char>, fmt::v7::format_args)
>>> referenced by dictionary_parser.cpp.obj
>>>               .../libcifpp.a
>>> referenced 20 more times
```

## 两处成因（互相独立，必须都处理）

### ① 上游 CMakeLists 里**可能根本没有 fmt** —— 且依赖普遍是 PRIVATE 链接

**实测（libcifpp v10.0.4）**：上游 CMakeLists 里搜索 fmt 的结果是 **0**：

```bash
$ grep -c 'find_package(fmt\|fmt::fmt' CMakeLists.txt
0
```

→ **fmt 是我替换 `std::format` 之后新引入的依赖**，上游并没有它。

而上游对第三方依赖普遍用 **PRIVATE**：

```cmake
target_link_libraries(cifpp PRIVATE SQLite::SQLite3)          # 306
target_link_libraries(cifpp PRIVATE ${PCRE2_LINK_LIBRARIES})  # 357
target_link_libraries(cifpp PRIVATE $<BUILD_INTERFACE:pcre2s>)
```

**PRIVATE 不向下游传播** → `libcifpp.a` 内部引用了 fmt 符号，但**每个链接它的目标都要自己补 `libfmt`**：

| 链接点 | 出处 | 后果 |
|--------|------|------|
| 库自身 | 根 `CMakeLists.txt` | `libcifpp.a` 内含 fmt 符号引用 |
| 上游测试 | `test/CMakeLists.txt` | 链接失败 → 需补链 |
| examples | `examples/CMakeLists.txt` | 链接失败 → 需补链或关闭 |
| 消费者 probe | `test_package/` | 链接失败 → 需补链 |

**判别方法**：报错里若出现 `in archive <lib>.a`，且引用者是库内 `.obj`，就是「**库需要、但没传播下来**」——属 PRIVATE 不传播，而非库缺失。

### ② fmt 的符号带 **inline namespace（主版本号）** —— 跨主版本不可互换

fmt 用主版本号做 inline namespace：

| fmt 版本 | `FMT_VERSION` | 导出符号 |
|---------|--------------|---------|
| 7.1.3 | `70103` | `fmt::v7::*` |
| 8.1.1 | `80101` | `fmt::v8::*` |

**实测**：我把 **fmt/8.1.1** 链给用 **fmt/7.1.3** 编译的 `libcifpp.a`，报错正是：

```
undefined symbol: fmt::v7::detail::vformat
```

—— 看着「都叫 libfmt」，实际命名空间不同，**符号解析不到**。改用 fmt/7.1.3 后 10/10 上游测试全部通过。

> ⚠️ 这条最容易误判：报错里带着 `fmt::v7::`，很容易让人以为「上游库有缺陷」或「fmt 包坏了」，实际只是**链接了错误的主版本**。**报错里的 `fmt::vN` 就是编译期主版本的直接证据**。

## 方案（替换时同步做齐）

### ① 补链 libfmt（且要覆盖**所有**链接点）

```cmake
# 若上游 CMakeLists 无 fmt：给库补
target_link_libraries(cifpp PRIVATE fmt::fmt)

# 下游目标（tests / examples）通常在自己那份 CMakeLists 里，最容易漏：
target_link_libraries(<test-target> PRIVATE ... <fmt-pkg>/lib/libfmt.so)
```

### ② 锁定 fmt 主版本与编译期一致

```python
# conanfile.py
self.requires("fmt/7.1.3")   # 主版本必须与替换时所含头文件一致
```

一旦确定，构建/复现环境就必须用同一主版本 —— **不可跨主版本互换**。

### ③ 收尾自检

**全部**链接点（库、tests、examples、test_package probe）都能过链接，再谈运行结果。

### 快速判别流程

```bash
# 1) 从报错反推编译期 fmt 主版本
#    undefined symbol: fmt::v7::... → 编译期是 7.x
# 2) 读编译期 fmt 的版本宏
grep -hoE "FMT_VERSION [0-9]+" <fmt-include>/fmt/core.h    # 70103 → 7.1.3
# 3) 交叉核对目标库的符号命名空间
llvm-nm -D <libfmt.so> | grep -oE "fmt::v[0-9]+" | head -1
# 4) 确认上游是否 PRIVATE（决定下游是否必须自行补链）
grep -n "target_link_libraries" <src>/CMakeLists.txt
```

## 备选（fallback）

若某子目标集合（如 examples）不值得为 fmt 补链，可将其**关闭**（`BUILD_EXAMPLES=OFF`）而非强行链接；但**必须**保留库自身与 `test_package` probe 的链接正确性，并如实说明关闭了哪些目标及原因 —— **不可把「关掉目标」写成「没有该目标」**。

## 禁止

- ❌ **只替换 include 与调用名、不处理链接**：替换会引入新依赖与符号需求，链接侧不处理必失败。
- ❌ **认为「链哪个版本的 fmt 都一样」**：符号带 `fmt::vN`，跨主版本不可互换。
- ❌ **把关闭的 examples 说成"上游没有"**：关闭是取舍，声明失真会被审查方按口径不实打回。

## 实证

- **libcifpp/10.0.4（PR #9565）**：94 处 `std::format` → `fmt::format`。
  - 成因①：上游 CMakeLists 无 fmt（计数 0）+ pcre2/SQLite3/eigen 均 PRIVATE → `test/CMakeLists.txt` 需补链 `libfmt.so` 才通过
  - 成因②：误链 fmt/8.1.1（80101）给 fmt/7.1.3（70103）编译的库 → `undefined symbol: fmt::v7::detail::vformat`；改用 7.1.3 后 **10/10 上游测试全过（112 个实际执行的 test case / 5,209,054 断言）**
  - **口径说明**：`grep -rc TEST_CASE test/` 合计 **120**（源码声明，含条件编译/辅助宏下的声明），而 ctest 实跑各可执行文件报告的 test case 之和为 **112**（60+17+9+11+5+2+3+1 + rename-compound 1 + spinner 3）。两者差 8 —— **源码声明数 ≠ 注册执行数**属正常；引用时以**可执行数（112）**为准更严谨。
  - 同源影响：examples 也因同一原因链接失败，最终以 `BUILD_EXAMPLES=OFF` 处理（examples 不被 install）
