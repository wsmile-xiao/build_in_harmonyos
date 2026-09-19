# editline 2.1.0 上游测试台账（双口径）

## 测试发现与统计口径

- 源码声明总数（`source_declared_total`）：8（test/Makefile.am 的 `TESTS` 列表：basic、utf8-move、utf8-delete、utf8-word、utf8-wrap、history、homeend、wrap-tmux.sh）
- 当前配置可执行总数（`configured_executable_total`）：8（Automake `TESTS` 全部实例化为独立 make check 目标）
- 实际执行并通过（`executed_passed_total`）：7
- 未运行/跳过：1（wrap-tmux.sh，SKIP exit 77，环境无 tmux，属于上游脚本自声明的 headless/CI 跳过路径）
- 失败：0
- **全量通过率：7/8 = 87.5%**（跳过计入分母不计通过）
- 当前配置可执行集合通过率：7/7 = 100%（补口径，不替代全量通过率）
- 断言统计：basic 11、utf8-move 4、utf8-delete 3、utf8-word 5、utf8-wrap 1、history 3、homeend 1，合计 28 项 PASS 断言

## 枚举台账（源码声明 → 构建条件 → 构建目标 → ctest/make 注册项 → 实际执行）

| 入口 | 源文件 | 分类 | 是否独立上游用例 | 构建目标 | make check 注册 | 实际执行 | 结果/原因 |
|---|---|---|---|---|---|---|---|
| basic | test/basic.c | 用户测试源 | ✅ | test/basic | TESTS 第 1 项 | ./basic | PASS 11/11（insert/backspace/补全等） |
| utf8-move | test/utf8-move.c | 用户测试源 | ✅ | test/utf8-move | TESTS 第 2 项 | ./utf8-move | PASS 4/4 |
| utf8-delete | test/utf8-delete.c | 用户测试源 | ✅ | test/utf8-delete | TESTS 第 3 项 | ./utf8-delete | PASS 3/3 |
| utf8-word | test/utf8-word.c | 用户测试源 | ✅ | test/utf8-word | TESTS 第 4 项 | ./utf8-word | PASS 5/5 |
| utf8-wrap | test/utf8-wrap.c | 用户测试源 | ✅ | test/utf8-wrap | TESTS 第 5 项 | ./utf8-wrap | PASS 1/1 |
| history | test/history.c | 用户测试源 | ✅ | test/history | TESTS 第 6 项 | ./history | PASS 3/3（64/8/200 三档容量 round-trip） |
| homeend | test/homeend.c | 用户测试源 | ✅ | test/homeend | TESTS 第 7 项 | ./homeend | PASS 1/1 |
| wrap-tmux.sh | test/wrap-tmux.sh | 测试脚本 | ✅ | test/wrap-tmux.sh | TESTS 第 8 项（SH_LOG_COMPILER=$(SHELL)） | make check 运行 | SKIP exit 77：环境无 tmux，脚本 `command -v tmux || exit 77` 上游自声明跳过路径（headless/CI 设计） |

### 非独立用例项（台账列出，不计入上游用例数）

| 入口 | 源文件 | 分类 | 说明 |
|---|---|---|---|
| eltest.c/eltest.h | test/eltest.c, test/eltest.h | 框架源码（pty 测试底座） | `check_LIBRARIES libeltest.a`，被各测试程序链接，非独立用例 |
| eltty | test/eltty.c | 辅助程序 | `check_PROGRAMS` 成员但**不在 TESTS**，仅 wrap-tmux.sh 在真实终端中驱动，非独立用例 |
| testit | examples/testit.c | 样例 | noinst_PROGRAMS，`--enable-examples` 默认关闭，未实例化 |
| cli | examples/cli.c | 样例 | 同上，未实例化 |
| excallback | examples/excallback.c | 样例 | 同上，未实例化 |
| fileman | examples/fileman.c | 样例 | 同上，未实例化 |

## 逐项映射（源码声明 → 构建条件 → 目标 → 注册项 → 日志）

1. `TESTS` 8 项均无条件编译宏 gate（无 `#ifdef` 互斥分支导致未实例化），全部实例化。
2. `check_PROGRAMS = basic utf8-move utf8-delete utf8-word utf8-wrap history homeend eltty`，其中 eltty 不在 TESTS（辅助）。
3. Automake `make check` 注册 8 项，实测 `PASS: basic ... PASS: homeend, SKIP: wrap-tmux.sh`（04-check.log，SHA-256 `37bd3111988459465935fdce40887967c69eb9cbaa0035c710f0cd192fbad35e`）。
4. 各用例单独复跑日志及 SHA-256：
   - test-basic.log `f466113998e4db8dfce83055785d995579691531e5e5646b694f2a77ff1cd158`
   - test-utf8-move.log `1f006c459fe6451272beff4da73e8c03f4a51abbd8f976b08d57d0af2e617c6e`
   - test-utf8-delete.log `596cd26a133dda87963b785648a8149824d54cc79e99d210bb11461d562ef0cd`
   - test-utf8-word.log `113bbf5e436d50d3560413b656a7fd0f3aa264ec96fca48a132a3baad8cb669f`
   - test-utf8-wrap.log `5e34a909d706be54fe9303298491b147330dd1584736005d39183972a18e6a26`
   - test-history.log `b20c2bf92ba6f4371258d135b982a32c90d3fe817543a2b7928e07e247dda2ff`
   - test-homeend.log `cee3592c4d638d4a4ed9e662ed41616276a3c3d0db3788213867248162610f73`

## wrap-tmux.sh 跳过说明（唯一未运行项）

- 首查：`command -v tmux` → 空（TMUX_MISSING，环境无 tmux），脚本第 1 个条件即 `exit 77`。
- 该跳过是上游脚本**显式设计**的 headless/CI 路径（脚本注释原文：*"Exits 77 (SKIP) when tmux is unavailable or unusable, so the suite still runs on headless machines and in CI"*），不属于失败或未实例化。
- 恢复条件：安装 tmux（如 `conan`/包管理提供）且存在可用的 pty/tmp 后重跑 `make check`。
- 该项计入全量分母（8）但不计通过，故全量通过率 7/8=87.5%。

## 统计口径结论

`executed_passed_total / source_declared_total = 7/8 (87.5%)`；当前配置可执行集合 `7/7 (100%)`。无未实例化项，无失败项。样例/基准/fixture/脚本均已在上方台账显式列出并说明不计入上游用例的理由。
