# cscope 15.9 — 测试报告（R51 三步法）

## 一、环境

| 项 | 值 |
|---|---|
| 平台 | HarmonyOS PC（aarch64），宿主 `uname -s` = `HarmonyOS` |
| 编译器 | OHOS clang 15.0.4（`/data/service/hnp/bin/clang`） |
| Conan | 2.29.1（OHOS 适配版） |
| Profile | `ci/conan/profiles/ohos-aarch64`（os=OHOS/6.0，arch=armv8，libc++，cppstd=17） |
| 依赖 | `ncurses/6.6`（静态，制品仓二进制） |
| 构建 | `conan create . -pr:h=… -pr:b=…`，rc=0 |

## 二、上游测试清点（R51 第 1 步：先清点）

**结论：上游 cscope 15.9 不附带任何测试套件。** 清点证据（对 pristine 源码
`cscope-15.9.orig/`，115 文件）：

| 清点项 | 结果 | 证据 |
|---|---|---|
| `tests/` / `test/` 目录 | 0 个 | `find . -type d -iname "*test*"` → 空 |
| 测试文件（`*test*` / `*.t`） | 0 个 | `find . -type f -iname "*test*"` → 空 |
| automake `TESTS =` 变量 | 0 处 | 四个 `Makefile.am`（顶层/src/doc/contrib）grep `^TESTS` → 空 |
| `check_PROGRAMS` | 0 处 | grep `check_PROGRAMS` → 空 |
| `check-local` 自定义目标 | 0 处 | grep `check-local` → 空 |
| `AC_CONFIG_TESTDIR` / autotest | 0 处 | `configure.in` 仅 `AM_INIT_AUTOMAKE`，无测试宏 |
| CI 配置（.travis/.github 等） | 无 | 顶层树无任何 CI 配置文件 |

`grep "check-am"` 在四个 `Makefile.in` 中命中，但均为 **automake 自动生成的
空默认规则**（`check-am: all-am` 后无任何命令体），不构成测试用例——这正是
R51 所警示的"清点不可凭 grep 命中数"情形，故此处按目录/变量/宏三维度交叉清点。

上游测试总数 **N = 0**，故 R51 第 2 步"运行上游测试"无对象可执行，第 3 步
以本文第三节的实测结果回填，并附上节清点证据（防"谎报为 0"）。

## 三、实际运行验证（R51 第 2/3 步：运行 + 回填实测）

### 3.1 test_package（`archives/c/cscope/15.9/test_package/`）

非空壳测试，跑真实 CLI 功能链路：

| # | 用例 | 命令 | 结果 |
|---|---|---|---|
| 1 | 版本横幅 | `cscope -V` 断言含 `version 15` | ✅ PASS |
| 2 | 建交叉引用库 | `cscope -b -f cscope.out sample.c`，断言 `cscope.out` 非空 | ✅ PASS |
| 3 | 行模式符号查询 | `cscope -d -f cscope.out -L -0 target_symbol`，断言命中 `target_symbol` | ✅ PASS |

用例 3 的实测输出（真实交叉引用结果）：

```
[test] cscope -V
cscope: version 15.9
✅ -V OK
[test] cscope -b（建交叉引用库）
[test] cscope -d -f cscope.out -L -0 target_symbol（行模式查询符号）
sample.c target_symbol 1 int target_symbol(int x) { return x + 1; }
sample.c caller 2 int caller(void ) { return target_symbol(41); }
✅ 功能查询 OK
```

### 3.2 完整消费者端到端用例（`test_e2e.sh`，鸿蒙特有测试，2026-10-03 新增）

消费者场景：cscope 的真实消费通道是编辑器/IDE 的 Cscope 集成（vim/emacs
等生成的协议客户端），查询全部经由 `cscope -d -L -<type> <pattern>` 行模式
接口完成。本用例在独立临时目录内对 `e2e-probe/` 微型 C 工程（main.c /
parser.c / parser.h / util.c / util.h，含跨文件调用与 `#include` 关系）走通
完整链路，共 7 例，逐例独立判定：

| # | 用例 | 命令 | 断言 | 结果 |
|---|------|------|------|------|
| 1/7 | 交叉引用库构建 | `cscope.files` 清单 → `cscope -b -f cscope.out` | `cscope.out` 非空 | ✅ PASS |
| 2/7 | 符号查询 -0 | `cscope -d -L -0 tokenize` | 定义（util.c）+ 调用点（parser.c）跨文件命中 | ✅ PASS |
| 3/7 | 函数定义 -1 | `cscope -d -L -1 parse_twice` | 命中 parser.c | ✅ PASS |
| 4/7 | 被调函数 -2 | `cscope -d -L -2 parse_input` | 列出其调用的 tokenize + checksum 调用点 | ✅ PASS |
| 5/7 | 调用者 -3 | `cscope -d -L -3 tokenize` | 命中调用方 parser.c | ✅ PASS |
| 6/7 | #include 关系 -8 | `cscope -d -L -8 util.h` | 命中包含方 parser.c + util.c | ✅ PASS |
| 7/7 | 增量更新 -u | 追加 `parse_three` → `cscope -b -u` → `-0 parse_three` | 新符号入索引，命中 parser.c | ✅ PASS |

真机实测输出摘录（conan create 内 test_package 执行，2026-10-03）：

```
======== Testing the package: Executing test ========
cscope/15.9 (test package): RUN: /data/service/hnp/bin/bash test_e2e.sh
== cscope version ==
cscope: version 15.9
----- -2 parse_input -----
parser.c tokenize 5 int n = tokenize(src);
parser.c checksum 6 return checksum(n);
----- -8 util.h -----
parser.c <global> 2 #include "util.h"
util.c <global> 1 #include "util.h"
TEST PASS: 1/7 交叉引用库构建（cscope.files 清单 → cscope -b -f cscope.out）
TEST PASS: 2/7 符号查询 -0 tokenize（定义 util.c + 调用点 parser.c 跨文件命中）
TEST PASS: 3/7 函数定义查询 -1 parse_twice（命中 parser.c）
TEST PASS: 4/7 被调函数查询 -2 parse_input（列出其调用的 tokenize + checksum 调用点）
TEST PASS: 5/7 调用者查询 -3 tokenize（命中调用方 parser.c）
TEST PASS: 6/7 include 关系查询 -8 util.h（命中包含方 parser.c + util.c）
TEST PASS: 7/7 增量更新 cscope -b -u（新函数 parse_three 入索引，命中 parser.c）
TEST SUMMARY: 7 passed, 0 failed
```

任一用例失败即以退出码 1 结束（`conan test_package` 捕获为测试失败）；
本次实测 `conan create` rc=0。

### 3.3 汇总（禁占位符，均为实测）

| 指标 | 值 |
|---|---|
| 上游测试总数 N | 0（清点证据见第二节） |
| 实际运行上游测试数 N′ | 0（上游确无测试可运行） |
| 上游测试通过率 | N/A（无测试套件） |
| 本库 test_package 用例数 | **10**（冒烟 3 + 端到端 7） |
| 通过 / 失败 / 跳过 | **10 / 0 / 0** |
| 其中完整消费者端到端用例 | 1 个（`test_e2e.sh`，7 例全链路；MANIFEST.`consumer_case_count`=1） |
| `conan create` | rc=0（真机复验 2026-10-03，含测试整改后的 test_e2e.sh） |
| `verify-build` 质量报告 | PASS（G1 ✅ / G2 ⚠️1(非阻断) / G3 ✅ / G4 ✅） |

G2 的 1 项 ⚠️ 为 verify-build 在其检查用的 install prefix 的 `bin/` 下
未发现可执行文件（`verify_build.py:125-140` 的门禁扫描 install prefix，
而非 conan 包内容），该 ⚠️ 不影响功能可用性判定；cscope 的 conan 包
实际安装 `bin/cscope`（见 `reports/conan-create.log` 与第三节
test_package 实测）。`verify-build` 总体裁决为 **PASS**。

## 四、适配中实测发现的运行时缺陷（已修复并有回归用例）

首次构建后 `cscope -d -L -0 <符号>`（行模式）报
`Cannot open file <TMPDIR>/cscope.<pid>/cscope.1`，功能不可用。根因经实测
定位为 HMDFS 权限语义差异：

- `src/main.c:512` 上游用 `umask(S_IRWXG|S_IRWXO)`（=077）后
  `mkdir(tempdirpv, S_IRWXU)`（=0700），在 HMDFS 上得到实际模式
  `02700 (drwx--S---)`；
- HMDFS 解析目录访问时依据**组位**而非属主位，组位被清零 → 紧随其后的
  `open("<tmpdir>/cscope.N/cscope.1", "wb")` 返回 `EACCES`。

实测矩阵（同一 HMDFS 卷上复刻源码逻辑）：

| umask | mkdir mode | 实得模式 | 目录内建文件 |
|---|---|---|---|
| 077 | 0700 | 02700 | ❌ EACCES |
| 007 | 0700 | 02770 | ✅ OK |
| 022 | 0700 | 02751 | ✅ OK |

修复：`patches/0004-src-main.c.patch` 将私有临时目录的 umask 放宽为
`S_IRWXO`（仍拒绝 other，保持仅本组可访问）。该目录由
`mkdir(tempdirpv, S_IRWXU)` 创建，在符合 POSIX 的文件系统上其组位/其他位
本就为 0，故放宽 umask 不改变实际模式；补丁不含平台宏、不含平台分支，
仅对按组位解析目录访问的文件系统（HMDFS）产生修复效果。修复后用例 3
通过（见 3.1）。

## 五、结论

cscope 15.9 在 HarmonyOS PC (aarch64) 上以 OHOS clang 15.0.4 构建成功，
`bin/cscope` 全部 **10 例实测通过**（冒烟 3 例 + 完整消费者端到端链路 7 例；
真机复验 2026-10-03，`conan create` rc=0）；上游无测试套件（清点证据见第二节），
适配过程中的行模式缺陷已定位、修复并纳入回归用例。
