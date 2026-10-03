# autotools 上游 TESTS 为空：make check 只构建不运行，测试清点必须下探 check_PROGRAMS

> 草稿（DRAFT）— 来自 libydpdict 1.0.4.1（PR !13886）的上游测试清点纠偏：
> 1.0.4（!12876）清点结论为「上游无 check_PROGRAMS、测试总数 N=0」，
> 1.0.4.1 实测修正为 **N=4** 并逐个真实执行。
> 与 `.kv` 同 stem 配对，字段见
> `knowledge/drafts/DRAFT-ydpdict-1.0.4.1-autotools-empty-tests-check-programs-audit.kv`

## 现象

对一个 autotools 上游包做测试清点时，会同时踩到两个假信号：

| 观察到的现象 | 实际含义 |
|---|---|
| 发布包内没有 `tests/` 目录 | 不代表没有测试资产（测试程序可能放在 `misc/`、`src/` 等目录） |
| 三个 `Makefile.am` 里都没有 `TESTS` 变量 | `TESTS` 空 ≠ 没有测试，只是 automake 测试驱动没有登记项 |
| `make check` 退出码 0 | 在 `TESTS` 为空时只代表**构建成功**，一个用例都没跑 |
| 清点结论 "N=0，上游无测试" | 误报：`check_PROGRAMS` 里躺着 4 个可运行程序 |

libydpdict 1.0.4 的真实清点记录就写成了 "上游无 check_PROGRAMS、测试总数 N=0"；
1.0.4.1 逐行读 `misc/Makefile.am` 后修正为 N=4。

## 根因

automake 里这是两个语义完全不同的变量：

- `TESTS` —— **要执行的测试**列表（automake 并行测试驱动 `test-suite.log` 的输入）；
- `check_PROGRAMS` —— 只是**要构建的测试程序**列表，构建完就结束。

libydpdict 1.0.4 官方 release tarball（40 个成员，无 `tests/` 目录）里：

```make
# misc/Makefile.am:1
check_PROGRAMS = ydpstress ydptest ydpxml gentable
EXTRA_DIST = mkdict.py

ydpstress_SOURCES = ydpstress.c
ydptest_SOURCES   = ydpstress.c      # 同源、独立二进制
ydpxml_SOURCES    = ydpxml.c         # 可选 libxml2 校验器
gentable_SOURCES  = gentable.c       # iconv windows-1250→utf-8 转换表
```

`src/Makefile.am`、`include/Makefile.am`、`misc/Makefile.am` **都没有 `TESTS`**。
于是预生成的 `misc/Makefile.in` 里只有构建规则：

```make
check-am: all-am
	$(MAKE) $(AM_MAKEFLAGS) $(check_PROGRAMS)
check: check-am
```

没有 `$(TEST_LOGS)` / `$(TEST_SUITE_LOG)` —— `make check` 把 4 个程序编译出来就返回 0。
**退出码 0 是构建结论，不是测试结论。**

两类后果：

1. **清点误报（少报）**：以「tests/ 目录 + TESTS 变量 + ctest/pytest 注册项」三面判据
   清点，三面全 0，于是 N=0。真实注册面在 `check_PROGRAMS`：N=4
   （其中 `ydptest_SOURCES=ydpstress.c`，与 `ydpstress` 同源、独立二进制，按 2 例计）。
2. **假通过**：把 `make check` 的退出码 0 当成"上游测试通过率 100%"。
   同族的"只构建不执行就宣称已执行"也是同一类误报。

本条与两条既有草稿同族但根因不同：

- `DRAFT-10251-libnfc-tools-1.8.0-autotools-test-framework-guard`：configure 守卫
  （`AM_CONDITIONAL` + 可选测试框架）把整套测试排除出构建，`make check` 报 `TOTAL: 0`；
- `DRAFT-mpsolve-3.2.3-make-check-green-is-not-deliverable-green`：check 程序只链构建树
  私有库、automake 把 SKIP 计入 TOTAL，绿不等于交付物可用；
- **本条**：既没有守卫、也没有 SKIP —— 是 `TESTS` 与 `check_PROGRAMS` 的变量语义
  被混淆，把"没登记执行驱动"读成"没有测试资产"。

## 处置（rec_approach: enumerate-check-programs-then-execute-each）

清点与执行分两步，两步都不依赖 `TESTS`：

**第一步 · 清点注册面**（任一非空都计入 N）

```bash
grep -n 'check_PROGRAMS\|check_SCRIPTS\|check_LTLIBRARIES\|^TESTS' \
     src/Makefile.am include/Makefile.am misc/Makefile.am
# → misc/Makefile.am:1:check_PROGRAMS = ydpstress ydptest ydpxml gentable
```

同时展开 `*_SOURCES` 识别同源多二进制、确认每个程序的外部数据依赖
（`ydpstress/ydptest/ydpxml` 按上游硬编码 `DICT_PATH=/usr/local/share/ydpdict`
读 `dict100/101/200/201.dat/.idx`；`gentable` 无数据依赖）。

**第二步 · 构建后逐个真实执行**

```bash
make -C misc check                     # 只负责构建
for p in ydpstress ydptest ydpxml gentable; do
  ./misc/$p || exit 1                  # 逐个真实执行，任一非 0 即失败
done
```

**测试数据**：上游商业词典（Young Digital Planet）不可分发、上游仓库也不提供；
配方按上游 `EXTRA_DIST` 里的官方合成工具 `misc/mkdict.py` 的同一二进制格式
合成 4 本词典作为测试数据（`<LLHHLL236s>` 索引头 + `<BBHL>` 条目 + `<L>` 正文），
**测试程序源码与判定逻辑零改动**。

**降级口径（fallback）**：平台 CI worker 根文件系统只读，`/usr/local/share/ydpdict`
建不出来 —— 此时 3 个数据依赖程序必须**显式跳过并写明原因**：

```
WARN: ydpdict test corpus NOT provisioned at /usr/local/share/ydpdict (...) ——
      目标环境只读根文件系统；数据依赖的上游测试（ydpstress/ydptest/ydpxml）本环境跳过
skip (no corpus at /usr/local/share/ydpdict): misc/ydpstress
skip (no corpus at /usr/local/share/ydpdict): misc/ydptest
skip (no corpus at /usr/local/share/ydpdict): misc/ydpxml
running upstream check program: misc/gentable → upstream check program PASSED: misc/gentable
```

同一提交在可写环境（本地 aarch64：OHOS clang + qemu-user + OHOS musl 运行根）
**4/4 真实执行通过**；DAYU200 真机消费者用例 23/23 通过、退出码 0。

## 禁止做法

- **禁止**只查 `TESTS` 变量或只看有没有 `tests/` 目录就下"上游无测试、N=0"的结论
  （必须下探 `check_PROGRAMS` / `check_SCRIPTS` / `check_LTLIBRARIES`）。
- **禁止**把 `make check` 的退出码 0 写成"上游测试通过率 100%"——`TESTS` 为空时它
  只是构建结论。
- **禁止**只构建不执行就宣称"上游测试已执行"。
- **禁止**为了让构建变绿而删除/注释/禁用 `check_PROGRAMS` 里的程序（违反 R51
  "上游测试原样执行"）；数据缺失只能显式跳过并说明理由，不得静默跳过、
  更不得把跳过计入通过数。

## 验证方式

| 面 | 命令 | 期望 |
|---|---|---|
| 建树面 | `tar -tzf libydpdict-1.0.4.tar.gz \| grep -c '/tests\?/'` | `0`（测试不在 `tests/`） |
| 变量面 | `grep -n 'TESTS\|check_PROGRAMS' src/ include/ misc/ Makefile.am` | 唯一命中 `misc/Makefile.am:1:check_PROGRAMS = ...` |
| 生成面 | `awk '/^check-am:/,/^$/' misc/Makefile.in` | 只有 `$(MAKE) ... $(check_PROGRAMS)`，无 `$(TEST_LOGS)` |
| 执行面 | `make -C misc check && for p in ydpstress ydptest ydpxml gentable; do ./misc/$p \|\| exit 1; done` | 可写环境 4/4 PASS；只读环境 3 例显式 skip + `gentable` PASS |

## 适用范围

- 所有以 autotools/automake 发布的上游，特别是 **release tarball 内已预生成
  `Makefile.in`、适配时不再重跑 `autoreconf`** 的包（`TESTS` 缺失会原样固化）；
- 所有按"测试目录 / TESTS 变量 / 框架注册项"三面判据做上游测试清点的流程
  （rule4 / R51 口径）与 PR/Issue 申报表；
- 所有拿 `make check` 退出码当测试证据的 CI 门禁；
- 不适用于：有正常 automake 测试驱动（`TESTS` 非空）的上游，或 CMake/CTest、
  meson 等其他构建系统（各自有对应的空套件假通过形态）。

## 查重（七轴）

- `exact_duplicate`：否 —— 图谱无"TESTS 为空 / check_PROGRAMS 下探"条目
- `causal_duplicate`：否 —— 与 10251（configure 守卫排除）、mpsolve（私有库 + SKIP 计入
  TOTAL）同属"退出码/汇总面 ≠ 执行面"，但根因是变量语义混淆，无守卫、无 SKIP
- `trigger_overlap`：部分 —— `make check`、`check_PROGRAMS`、`TOTAL: 0` 与既有条目触发词重合
- `solution_overlap`：部分 —— 与"逐个真实执行上游 check 程序"的既有做法同族
- `combination_novelty`：有 —— 把"清点注册面（check_PROGRAMS/check_SCRIPTS/TESTS）→
  构建与执行分离 → 数据依赖显式降级"合成一条可复用清单
- `boundary_novelty`：有 —— 明确区分 `TESTS`（执行列表）与 `check_PROGRAMS`（构建列表）
  这两个被普遍混淆的变量
- `test_migration_novelty`：有 —— 给出四步可复现验证（建树面/变量面/生成面/执行面）

## 相关

- `similar_to`：`DRAFT-10251-libnfc-tools-1.8.0-autotools-test-framework-guard`、
  `DRAFT-mpsolve-3.2.3-make-check-green-is-not-deliverable-green`、
  `DRAFT-no-upstream-tests-drive-real-interface`
- `principles`：P-BUILD-001（平台限制必须降级而非绕过——降级必须显式、不得静默）
