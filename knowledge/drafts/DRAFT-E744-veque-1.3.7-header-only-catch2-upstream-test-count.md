# DRAFT-E744：无构建系统 header-only 包的自带 Catch2 单头测试——按 TU 分程序链接 + 四口径清点（veque 1.3.7 实测）

> Contributor: veque 1.3.7 适配任务 | Status: Draft | Updated: 2026-09-25
> Source: 任务卡 `veque` 1.3.7（新适配 header-only，分支 `feat/veque-1.3.7`）
> 关联：DRAFT-jsoncons-1.9.0-test-count-and-baseline-noise（注册→运行双口径）、
> DRAFT-cdt-1.4.5-catch2-21310-amalgamated-test-adaptation、DRAFT-ctpg-1.3.7-catch2-ctest-module-injection

## 背景

`veque` 1.3.7 是 header-only C++17 容器（单头 `include/veque.hpp`），上游 tarball **没有任何
构建系统**（无 `CMakeLists.txt` / `Makefile` / `configure`），测试树 `test/` 自带 Catch2 v2 单头
`catch.hpp`（657 KB）+ `main.cpp`（`CATCH_CONFIG_MAIN`）+ 10 个测试源。于是「上游测试怎么跑」
没有任何现成入口，必须自己搭；实测在鸿蒙 PC（clang 15.0.4 / libc++ / aarch64-unknown-linux-ohos）
上踩到两个**必然**的坑与一个**计数**坑。

## 三个坑（均为必然命中，不是偶发）

### ① 只给测试树 include 目录 → 上游测试 0 执行

```text
$ clang++ -std=c++17 -I <src>/test -c <src>/test/test_deque_parity.cpp
test/test_types.h:16:10: fatal error: 'veque.hpp' file not found
#include "veque.hpp"
        ^~~~~~~~~~~~
1 error generated.
```

测试源用相对名 include 库头，而库头在 `include/` 下 → 必须 `-I <src>/test -I <src>/include`
**两个** include 目录。只报一个文件找不到，形态极像「上游不兼容本平台」，实际是编译命令少给了一条 `-I`。

### ② 多个测试 TU 一次链接 → duplicate symbol（上游构建缺口，非平台问题）

`test/test_types.h` 在头文件里对变量模板做**无 `inline` 的显式特化**：

```cpp
template<typename T, size_t index> const T val;
template<> const int val<int,0> = 0;
template<> const std::string val<std::string,0> = std::string(100, 'A');
```

每个包含它的 TU 都会产出强符号，`clang++ *.o` 一次链接必然失败：

```text
ld.lld: error: duplicate symbol: val<std::__n1::basic_string<char,...>, 5ul>
>>> defined at test_deque_parity.cpp
>>> defined at test_strong_exception_guarantee.cpp
```

上游无构建系统、**从未把这些 TU 链接在一起**，所以这是上游构建缺口而不是 OHOS/clang 特有问题。
正确处置：**按 TU 分程序**——`main.o` 分别与每个测试 `.o` 链成 `bin_<name>`，逐个运行；
不改上游源码（不加 `inline`），也不用 `-Wl,--allow-multiple-definition` 掩盖问题。

### ③ 计数口径：源码宏 10 ≠ 框架注册 800

上游测试用的是 Catch2 的**模板用例宏**，一处宏会展开成几十上百个 case：

| 测试源 | 宏 | 展开 | 注册 case |
|---|---|---|---|
| test_deque_parity.cpp | `TEMPLATE_PRODUCT_TEST_CASE` | 4 模板 × 16 类型组合 | 64 |
| test_end_growth.cpp | `TEMPLATE_PRODUCT_TEST_CASE` | 4 模板 × 32 类型组合 | 128 |
| test_hashing.cpp | `TEMPLATE_LIST_TEST_CASE`（`MyTypes`） | 类型清单 48 项 | 48 |
| test_insert_erase.cpp | `TEMPLATE_PRODUCT_TEST_CASE` | 4 模板 × 16 类型组合 | 64 |
| test_insertion_growth.cpp | `TEMPLATE_PRODUCT_TEST_CASE` | 4 模板 × 16 类型组合 | 64 |
| test_ordering.cpp | `TEMPLATE_PRODUCT_TEST_CASE` | 4 模板 × 16 类型组合 | 64 |
| test_reassignment.cpp | `TEMPLATE_PRODUCT_TEST_CASE` | 4 模板 × 16 类型组合 | 64 |
| test_resize.cpp | `TEMPLATE_PRODUCT_TEST_CASE` | 4 模板 × 32 类型组合 | 128 |
| test_strong_exception_guarantee.cpp | `TEMPLATE_PRODUCT_TEST_CASE` | 4 模板 × 32 类型组合 | 128 |
| test_vector_parity.cpp | `TEMPLATE_PRODUCT_TEST_CASE` | 3 模板 × 16 类型组合 | 48 |
| **合计** | 源码宏 **10 处** | | **800** |

`grep -c 'TEST_CASE('` 只有 10，`--list-test-names-only` 与实跑都是 **800**；
assertion 运行期 **13,762,477**（`SECTION`/循环/rand 驱动）。三种口径必须分列：
**N 取最大候选 800**（框架注册 = 实跑），10 处宏与 800 的差额按上表逐文件归因，
assertion 只作附注不作 N——否则任一方向都会撞审方清点（声明 10 → 实测 800 判少报；
声明 800 却按 10 解释 → 口径不自洽）。

## 复现命令（设备可直接执行）

```sh
SRC="$HOME/ws/tmp/builds/veque-1.3.7.work"
BLD="$TASK_DIR/upstream-test"
CCXX=/data/service/hnp/bin/clang++
INC_OPTS="-I $SRC/test -I $SRC/include"      # ① 两个 include 目录

# 逐 TU 编译，逐个判 rc
for f in "$SRC"/test/*.cpp; do
  "$CCXX" -std=c++17 -O0 $INC_OPTS -c "$f" -o "$BLD/$(basename "$f" .cpp).o" || exit 2
done

# 按 TU 分程序链接（② 不要一次链 *.o）
for f in "$SRC"/test/test_*.cpp; do
  b=$(basename "$f" .cpp)
  "$CCXX" -std=c++17 -O0 "$BLD/main.o" "$BLD/$b.o" -o "$BLD/bin_$b" || exit 3
done

# 沙箱 HOME 下：注册数 → 实跑（③ 两口径都要留证）
for b in "$BLD"/bin_*; do
  HOME="$TASK_DIR/test-home" "$b" --list-test-names-only | wc -l
  HOME="$TASK_DIR/test-home" "$b"
done
```

## 实测结果（2026-09-25，HarmonyOS PC aarch64）

- 编译：11 个 TU 全部 `rc=0`（`-O0`；重模板 TU 在 loadavg≈21 时单个可达数分钟，重活需持 build slot）
- 链接：10 个测试程序全部 `rc=0`
- 注册：`--list-test-names-only` 合计 **800** case
- 实跑：**800/800 全过**，逐程序输出 `All tests passed (N assertions in M test cases)`
  （64/128/48/64/64/64/64/128/128/48 case，断言合计 13762477），`rc=0` ×10，无 skip、无 not-run
- 消费者：`test_package` 真断言 **67** 条 `VEQUE-CONSUMER checks=67 failures=0`
- 证据：`$TASK_DIR/upstream-test/{run2.log,run3.log,summary.tsv}`、
  `archives/v/veque/1.3.7/reports/test-report.md`

## 推广价值

适用「header-only + 上游无构建系统 + 自带单头测试框架」的整类包（同批在途：boolinq、crcpp、
tclap、embedded_ringbuf_cpp 等）：任何一条不处理，上游测试都会**一个都跑不到**，
而失败形态（找不到头 / 链接重复符号 / 0 用例全绿）都极易被误判成「平台不兼容」或「上游没测试」。
