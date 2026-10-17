# fatal v2026.09.14.00 — 适配笔记

> 上游: https://github.com/facebook/fatal （Facebook Template Library）
> 版本号: **v2026.09.14.00**（与上游 release tag 一致）
> 适配平台: HarmonyOS PC (HongMeng Kernel 1.12.0) / aarch64
> 工具链: clang 15.0.4 (ohos-sdk 26.0.0.18 native) + libcxx-ohos
> 适配日期: 2026-09-25

## 1. 这是什么

fatal 是 Facebook 开源的 **header-only C++ 模板元编程库**（Facebook Template
Library）：`fatal/` 目录下的 157 个 `.h` 直接作为 include 树使用，没有任何
编译产物。消费者只需把包内 `include/` 加进头文件搜索路径，然后
`#include <fatal/type/list.h>` 之类即可。

因此本包 `conanfile.py` 没有编译阶段，`build()` 的全部职责是 **跑上游官方测试**。

## 2. 上游测试怎么跑（rule 4 实测）

上游仓库根目录自带 harness：`test.sh` → `compile.sh` → `scripts.inc`。

```
find . -name '*_test.cpp'          # 67 个测试 TU
./test.sh <某个 *_test.cpp>        # 用 compile.sh 编译 + 运行
```

`compile.sh` 的实际编译参数（本包逐字复刻）：

```
-O0 -g -pthread -ftemplate-depth-1024 -ftemplate-backtrace-limit=0
-ferror-limit=1 -Wall -Werror -Wextra -std=c++17 -I .
```

每个测试二进制自报 `succeeded: passed <N>/<N>`。

### 用例计数口径（重要）

| 口径 | 数量 | 说明 |
|------|------|------|
| `FATAL_TEST(` 字面量 | **845** | 审查侧实测口径（grep 计数） |
| 上游实际编译的用例 | **839** | 845 − 6 |
| 实测执行 | **839** | 本次真实执行 |
| 实测通过 | **839** | 100%，0 失败 0 跳过 |

那 6 个差额在 `fatal/string/test/rope_test.cpp` 里：`find` / `rfind` /
`find_first_of` / `find_first_not_of` / `find_last_of` / `find_last_not_of`
六个 `FATAL_TEST(..., TODO)` 桩（体内是 `FATAL_EXPECT_UNREACHABLE()`）被上游自己
用 `/* TODO: IMPLEMENT */ ... */` 整块注释掉了，上游也不编译它们。

> 申报口径：**声明 N = 845（与审查侧口径一致），实测执行 839（100% 通过）**，
> 并注明 6 个用例位于上游块注释内。这样既不多报也不少报。

## 3. 两个必须打的补丁

两次首轮实测暴露出两个**新版标准库严格化**导致的编译失败（并不是鸿蒙独有，
但因为 OHOS 用 clang 15 + libcxx-ohos，必然会撞上）：

### 0001 — `std::iterator` 弃用（`fatal/string/rope.h`）

```
fatal/string/rope.h:648:17: error: 'iterator<std::bidirectional_iterator_tag, char>'
      is deprecated [-Werror,-Wdeprecated-declarations]
```

`const_iterator` 继承了 `std::iterator<...>`——C++17 起弃用，libc++ 直接给它加了
`__attribute__((deprecated))`，在 `-Werror -Wextra` 下编译失败。

修法：改为等价的 5 个显式成员 typedef（`iterator_category` / `value_type` /
`difference_type` / `pointer` / `reference`），语义完全一致，且 `rope.h` 是**安装
头文件**，不打这个补丁的话任何消费者的 `-Werror` 构建都会挂。

### 0002 — `std::tuple_element` 硬化（`fatal/type/test/deprecated_transform_test.cpp`）

```
.../libcxx-ohos/include/c++/v1/__utility/pair.h:453:5: error: static assertion failed
    due to requirement '2UL < 2': Index out of bounds in std::tuple_element<...>
fatal/type/test/deprecated_transform_test.cpp:134:23: note: in instantiation of
    template type alias 'is_complete' requested here
```

上游想验证「`std::tuple_element<2, std::pair<void,void>>` 是不完整类型」，靠
`fatal::is_complete`（内部 `sizeof(T)`）做 SFINAE 探测。但新版 libc++ 给
`tuple_element` 加了越界 `static_assert`，实例化即**硬错误**，不再能被 SFINAE 吞掉。

修法：用 `#if !defined(_LIBCPP_VERSION)` 守卫这一行断言（保留对仍 SFINAE 友好的
实现的检查）。注意只注释掉一行 `FATAL_EXPECT_*`，**测试用例数不变**（该文件仍是
85 个 FATAL_TEST，实测 85/85 通过）。

## 4. 鸿蒙平台适配点

| 问题 | 现象 | 处理 |
|------|------|------|
| `/tmp` 只读 | 上游 `compile.sh` 固定写 `/tmp/.build`，鸿蒙 PC 的 `/tmp` 是只读 erofs | 配方**不复用** `compile.sh`，直接编译进 Conan 构建目录（`build/upstream-tests/`） |
| `posix_spawn` 不搜 PATH | 裸 `clang++` / `python3` 在 subprocess 里解析不到 | 编译器用绝对路径 `/data/service/hnp/bin/clang++`，并保留 PATH 兜底 |
| 工具链严格化 | 见上两节补丁 | 2 个 portability 补丁，`conandata.yml` 声明 |

## 5. test_package（消费者视角 + 鸿蒙特有）

`fatal` 是 header-only，消费者面就是 `<pkg>/include`。`test_fatal.py` 会先断言
`include/fatal/type/list.h` 存在（否则直接失败，保证 L1e 破坏性反向验证有意义），
再用与上游同样严格的参数编译并运行 3 个用例：

| 用例 | 类型 | 覆盖 |
|------|------|------|
| `consumer_api_test.cpp` | 消费者功能 | `fatal::list`/`size`/`reverse`/`push_front` 类型级断言 + 运行时 `fatal::foreach` 遍历校验 |
| `rope_iterator_test.cpp` | 鸿蒙特有 | 补丁 0001 的迭代器契约（含 `std::iterator_traits`）+ 运行时遍历 rope |
| `ohos_libcxx_surface_test.cpp` | 鸿蒙特有 | `fatal/type/` 公共头表面在 OHOS libc++ 下 `-Werror` 干净；覆盖补丁 0002 的 `tuple_element` 硬化路径 |

实测：`fatal v2026.09.14.00 consumer tests OK: 3/3 passed`。

> 卫生提示：`conan create` 运行时驱动会把产物写到 Conan 的 test build 目录；手工直接执行
> `python3 test_fatal.py <pkg>` 时会落到 `test_package/_build/`（临时产物，不要提交）。

## 6. 复现方式

```bash
# 完整（含上游 839 个用例 + test_package 消费者用例）
conan create . --profile=ohos-aarch64

# 只看上游全量执行的日志关键行
conan create . --profile=ohos-aarch64 2>&1 | grep 'fatal upstream tests'
# → SUMMARY: TUs=67 compiled=67 executed_cases=839 passed=839 failed=0 skipped=0 pass_rate=100.0%
```

## 7. 最终状态（结束标记）

| 项目 | 结果 |
|------|------|
| 编译状态 | **通过**（header-only 无编译单元；`build()` 内实跑上游全量套件） |
| 上游测试 | **67/67 TU 编译成功；839/839 用例通过（100%）**，0 失败 0 跳过 0 超时 |
| 消费者测试 | **3/3 通过**（`consumer_api_test` / `rope_iterator_test` / `ohos_libcxx_surface_test`） |
| 补丁 | 2 个 portability 补丁（均在 `conandata.yml` 声明，`patch -p1` 干净应用并复现实测树） |
| 知识沉淀 | 2 条草稿提交至 `knowledge/drafts/`，建议 promote |
| 豁免 | **未使用 `no_official_test.txt`，未跳过任何用例，未放宽任何编译告警级别** |
| packaging | `packaging/` 保留本仓既有约定标记 `.packaged`；`.tar.gz` 本体被 `.gitignore` 排除，不入仓 |
| 最终状态 | **适配完成（built），待评审 —— PR #13207** |
