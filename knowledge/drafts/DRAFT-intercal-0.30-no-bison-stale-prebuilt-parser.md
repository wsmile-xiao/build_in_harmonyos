# DRAFT-intercal-0.30-no-bison-stale-prebuilt-parser — 发行 tarball 自带旧-era 预生成 parser/lexer，而 OHOS 目标无 bison/yacc：只能播种自带旧件 + 把 .y/.l mtime 调旧以阻止 make 重生成，代价是编译器语法覆盖面停留在旧 era，须按平台受限逐项申报而非静默删

> **Contributor**: hw-4 | **Status**: DRAFT（最终编号由知识库主编确认） | **Updated**: 2026-09-24
> **Severity**: blocking (3) | **Category**: autotools / bison / yacc / flex / prebuilt-generated / parser / ohos / test-scope
> **Audience**: 在 OHOS/Conan 环境下构建「tarball 自带 parser.c/lexer.c 预生成物、但目标机无 bison/yacc/flex」的 autotools 老项目配方维护者

## 触发（trigger）

- 上游 **release tarball 自带 parser/lexer 的预生成 `.c`**（intercal 0.30 在 `prebuilt/` 里随包发布 `parser.c`/`lexer.c`/`oil-oil.c`，生成时间戳为 2010 年）。
- 目标 OHOS 设备 **无 bison / 无 yacc / 无 flex**（`command -v bison yacc flex` 全空）。configure 的 `AC_PROG_YACC` 探不到 → `YACC` 被置空（`YACC = :` 或空），`AC_PROG_LEX` 同理。
- 且 **源树同时发布了比预生成物更新的 `.y`/`.l` 语法源**（intercal 的 `parser.y`/`lexer.l`/`oil.y` 含 2010 之后的 ICL997I 等新语法），预生成 `.c` 与 `.y/.l` 不是同一 era。

## 症状（symptom）

- 直接 `make`：`.y→.c`/`.l→.c` 规则因 `$(YACC)`/`$(LEX)` 为空而空转或报 `No rule to make target`；或规则回退去 `mv y.tab.c` 而 `y.tab.c` 从未生成。
- 若强行保留自带旧 `parser.c` 让它编译通过，`ick`（编译器）二进制能建出来，但 **用 0.30 自身的旧语法子集以外的程序去喂 `ick`，报出旧 parser 不认识的新语法错误码**（如 `ICL997I` 一族），即「编译器的语法覆盖面停在 2010 era」。
- 上游 PIT 回归测试里那些新语法用例（intercal 0.30 的 `pit/` 共 30 个静态用例中约 20 个）在旧 parser 下无法通过——**这不是配方 bug，是目标无 bison 导致 parser 停留在旧版的平台能力缺失**。

## 根因（root cause）

发行 tarball 惯例上是「维护者机器上生成好 parser 再打包」，预生成物冻结在打包当时的 grammar 版本；一旦目标环境缺 bison/yacc，配方既不能用当前 `.y/.l` 重生成（工具不在），只能回退用旧 `.c`，于是构建出的编译器语法版本被钉死在旧 era。**关键：预生成 `.c` 与随包 `.y/.l` era 不一致时，make 会因 `.y/.l` mtime 更新而尝试用空的 `$(YACC)` 重生成，必须显式让 `.c` 比 `.y/.l` 新，才能锁定使用旧件。**

## 修复（rec，主方案）：播种自带旧件 + 调旧 `.y/.l` mtime 阻止重生成

在 recipe `build()` 内、`configure` 之后 `make` 之前：

1. 把自带 `prebuilt/{parser.c,lexer.c,oil-oil.c}` 拷进源码树它们该在的位置（intercal 需同时喂 `./` 与 `./src/` 两份拷贝点）。
2. 对每个语法源 `parser.y`/`lexer.l`/`oil.y`（含 `src/` 下的）用 `os.utime(fp, (atime, mtime - 10))` 把 mtime 调到比刚拷入的 `.c` 更旧，使 make 判定 `.c` 已最新、不再触发空 `$(YACC)` 的重生成规则。
3. **诚实申报语法覆盖面缺口**：把因此无法通过的新语法 PIT 用例逐个归为「平台受限·跳过（目标无 bison，parser 冻结于 2010 era）」，写入 `test_package/MANIFEST.yml` 的 `platform_limited` 与 `N_skipped`，**绝不为凑通过率静默删除用例或缩小分母**（AGENTS §10 / SKILL R34/R51）。

```python
import os
from conan.tools.files import copy

# build() 内，configure 之后 make 之前
for gen in ("parser.c", "parser.h", "lexer.c", "oil-oil.c"):
    copy(self, gen, os.path.join(src, "prebuilt"), src, keep_path=False)
    copy(self, gen, os.path.join(src, "prebuilt"), os.path.join(src, "src"), keep_path=False)
# 让拷入的 .c 比 .y/.l 新：把语法源 mtime 调旧，阻止空 YACC 重生成
for newer in ("parser.y", "lexer.l", "oil.y",
              os.path.join("src", "parser.y"), os.path.join("src", "lexer.l"),
              os.path.join("src", "oil.y")):
    fp = os.path.join(src, newer)
    if os.path.isfile(fp):
        st = os.stat(fp); os.utime(fp, (st.st_atime, st.st_mtime - 10))
```

## 反例 / 禁止（forbid）

- **禁止伪造 parser.c**：自己手写或从别处拷一个「能编过」的 parser.c 冒充——语法行为与上游 `.y` 不一致，错误延迟到运行期且不可审计。只用上游**随包发布**的那份旧件。
- **禁止静默删新语法用例**：把旧 parser 不认的用例从 `pit/` 里删掉以达 100%——触发 rule4 少报，且掩盖了真实平台能力缺失。必须逐项 `test_skipped` 附技术原因。
- **禁止 `tool_requires("bison/...")` 绕过**：若制品仓 bison 在 OHOS 上另有 m4sugar datadir 坑（见 DRAFT-bison-ohos-datadir-m4sugar），且重生成的 parser 又引入新的 era 不匹配，得不偿失；本包选择「接受旧 parser + 如实申报覆盖面」而非引入 bison 链。

## 适用范围与边界（scope / 解除条件）

- 适用：tarball 自带 parser/lexer 预生成 `.c`、目标无 bison/yacc/flex、且预生成物 era 旧于随包语法源的 autotools 老项目。
- 与 **DRAFT-autotools-ac-prog-lex-demotes-lex-when-libfl-unlinkable** 是**镜像关系**：那条是「工具在、lib 探测失败导致 LEX 降级 → make 前用上游命令**重生成**」；本条是「工具**不在** → 只能用随包旧件 + 调 mtime **阻止重生成**，并申报覆盖面损失」。签名不同（`LEX=:`+缺 lex.yy.c vs `YACC=`空+ICL 新语法拒绝），解法方向相反。
- 与 **E528（OHOS autotools env closure）** 正交：E528 管 TMPDIR/llvm-ar/HMDFS mktemp 环境闭环；本条管 parser 生成物 era 与覆盖面。
- 解除条件：目标 OHOS 环境提供可用 bison/yacc（含其 m4 数据目录正确），可从 `.y/.l` 现生成当前 era 的 parser 时，本「播种旧件 + 调 mtime」的退路不再需要，覆盖面缺口归零。

## 真实验证（intercal 0.30 设备实测）

- 播种 `prebuilt/*.c` + 把 `.y/.l` mtime 调旧后，`ick`/`convickt` 在 OHOS aarch64（clang 15 / libc++）成功编译安装。
- 消费者测试：`test_package` 用 `ick -b hello.i` 编译 INTERCAL hello 程序并链接成可执行，运行输出 `hello, world` 断言通过。
- 上游 PIT：配方在 `build()` 内用上游自带 `regresscheck` **逐例驱动**（上游 `make test` 把所有测试二进制设为先决条件，任一编译失败即整体跳过 → 0 执行，故不能直接跑 umbrella 目标）。实测真机 **pass=7 / fail=0 / skip=23**：旧 parser 支持的 7 例全过；23 例按平台受限逐项归因（noexe 20 = 新语法被 ICL997I/ICL405I 编译期拒绝；nochk 2 = quine/yapp 随包无 `.chk`，由运行时动态生成；timeout 1 = tests/count 按设计死循环），**静态 30 / 执行 7 / 跳过 23 / 消费者 1**，与 notes/MANIFEST/README 四处同源。
- `conan create` rc=0；`conan-verify` G1/G2/G3/G4 全 PASS。
