# jellyfish1 1.1.11 知识候选台账（四范围查重 + 判据 + 路径判断）

生成时间: 2026-09-25（B 机，整改第 3 轮前置文字面）
被检 HEAD: d6911a997b0538fe6b7feada1c554d5b5a5ed50a（分支 feat/jellyfish1-1.1.11）
查重范围: 正式知识 knowledge/doc/、图谱 knowledge/graph/（index.tsv + E*.kv）、
草稿 knowledge/drafts/、既有库归档 archives/
工具面: `python3 scripts/ohc-run.py draft-review <DRAFT-ID>`（其相似度语料只有
knowledge/graph/，**不扫 knowledge/drafts/**，故池内相似面另行人工 `grep -ri` 扫，
逐条计数见下）、`bash ci/scripts/knowledge_check.sh`、`bash ci/scripts/junk_check.sh`
证据件: ~/tmp/uc2/z33-jellyfish1-fix3/dedup.log（四范围手工查重原始输出）、
~/tmp/uc2/z33-jellyfish1-fix3/validate.log（.kv 三验：safe_load / 签名 re.search / 仓内解析器）

## 候选 1：抛出析构位于「被交付的库头」⇒ 消费者路径一律 std::terminate

- 真实错误（一手 `~/tmp/uc2/z33-jellyfish1/tc4-r2/tc4-r2.out`）：
  `:23` `libc++abi: terminating due to uncaught exception of type err_t: eraise from
  library side` + `:25 RC[unfixed.runstatic]=134`；
  `:40-42` 共享链法同为 RC=134；`:63` 真包上的
  `libc++abi: terminating due to uncaught exception of type
  SquareBinaryMatrix::SingularMatrix: Matrix is singular`；
  编译期先兆 `:9` `-Wexceptions` + `:12` `note: destructor has a implicit
  non-throwing exception specification`（:12 的 file:line 是探针自建头
  `libtc4.hpp:9:3`、其析构同名 `~raise_t` ⇒ **不是本包 err.hpp 的编译留痕**，只作
  该诊断的同形示例；全域检索该文案的一手出处只有 `tc4-r2.out:12/:20/:30/:37` 与
  同目录四份 `log.unfixed.*`）
- 抛点位置（一手，本轮用草稿的 `prescan_pattern` 直接在真件上扫出，见
  validate.log 第 3 节）：`jellyfish/err.hpp:123`
  `~raise_t() { throw err_t(oss.str()); }`（未打补丁树）与
  `:139` `#define eraise(e) if(1) err::raise_t<e>()` —— **即该头被安装、被消费者
  包含，且 eraise 是全库错误上报的唯一惯用法**
- 修复: 补丁 0001 一行 `noexcept(false)`；两臂 RC 从 134 → 0
  （`tc4-r2.out:52`、`:60`）
- 验证: 未打补丁的探测树 `make check` 为 **19 of 19 failed**
  （probe-check.log:44、probe/src/test-suite.log:5）；打 0001 后同一棵树为
  4 PASS + 15 FAIL + 1 SKIP（probe5b-check.log 判决行、汇总 :39）；
  交付轮 conan create 同读数（reports/w3-local-ci.log:788、:767/:773/:783/:786、:800）
- 适用范围: 被交付库头里存在「析构中 throw」惯用法、且以 C++11+ 标准构建的 C++ 库

### 四范围查重（逐范围实测，计数口径 = 命中文件数）

⚠ **计数单位与自排除口径**（本轮实测复算）：下表每格是**命中文件数**，且 drafts 一列
**不含本草稿自身两件**（`DRAFT-jellyfish1-1.1.11-shipped-header-throwing-destructor-noexcept-false.{kv,md}`）
⇒ 含本草稿时 `knowledge/drafts` 的宽口径 `noexcept` 为 **12 件**（既有 10）、字面
`noexcept(false)` 为 **6 件**（既有 4）。汇报口径不得写成一个介于两者之间的数
（第 3 轮审计否证过一处「drafts 内 noexcept 11 处」的口头计数：它既不是文件数也不是
既有条目数）。

| 范围 | 字面 `noexcept(false)` | noexcept | non-throwing exception specification | implicit noexcept | Wexceptions | throwing destructor | destructor |
|---|---|---|---|---|---|---|---|
| knowledge/graph | 1（E293.kv:41-43，动态异常规范族） | 1 | 0 | 0 | 0 | 0 | 1 |
| knowledge/doc | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| knowledge/drafts | 4（E543-draft-7707 的 .kv/.md；DRAFT-cxx17-removed-constructs 的 .kv/.md） | 10 文件 / 21 行 | 2 | 1 | 2 | 0 | 13 |
| archives | 11（jellyfish1 自身 4、boolstuff 4、aldo 1、glaze 1、libfex 1） | 430 | 1 | 0 | 2 | 2（均为本包自身 README.md/manifest.yaml） | 141 |

⚠ 口径说明: 表里「字面 `noexcept(false)`」一列取自 dedup.log 的**字面清单段**
（`grep -ril 'noexcept(false)' knowledge/ archives/`，共 16 件 = graph 1 + drafts 4 +
archives 11）。同一条脚本里以 BRE 转义写法 `noexcept\(false\)` 扫各范围时返回 0。
**归因更正（第 3 轮审计复算，旧表述「设备侧 toybox 对转义括号的处理差异」是错的）：
那不是工具缺陷，而是 POSIX BRE 的正常分组语义** —— BRE 里 `\(` `\)` 是捕获分组，
该式实际匹配的是字面串 `noexceptfalse`，故返 0 属正确行为 ⇒ 这个 0 不能当「不存在」
的判据（要匹配带括号的字面串就直接写 `noexcept(false)`，本轮复跑该写法在
`knowledge/drafts` 命中 6 件 = 既有 4 + 本草稿 2）。原始两份输出都在 dedup.log。

- **`terminate` 与 `destructor`/`析构` 同时出现的池内文件**（手工筛，dedup.log
  「抛出析构族」段）：只有 `E543-draft-7707.md` 与 `E543-draft-7707.kv` 一份机制。
  ⇒ 池内相似面**唯一**近邻就是被对照的那条。
- ⚠ `noexcept` 在 drafts 的 10 个文件里，除 E543-draft-7707 外**全部是另一种机制**：
  `DRAFT-commata-1.3.1-libcxx-sso-owned-string-move`、
  `DRAFT-cxx17-removed-constructs-compile-out-via-feature-macro`、
  `DRAFT-libfex-0.1.0-std-expected-polyfill-libcxx15`、
  `DRAFT-libfork-3.6.0-libcxx-missing-headers`、`DRAFT-ncmpc-libcpp15-cxx20-compat`
  —— 即 libc++ / SVO / `std::expected` 期望值族，与「析构里 throw」不是同一件事，
  **不得写成"同族"来充当查重结论**。
- ⚠ `noexcept(false)` 字面相同的三处（`E293.kv:41-43`、`boolstuff/0.1.16` 补丁 0002、
  `aldo/0.7.8/conanfile.py:363-387`）都是 **C++17 删除动态异常规范**的**编译期**修复
  （普通成员函数上的 `throw(Error)` / `throw(AudioException)`），与本条的
  **运行期 terminate**（析构隐式 noexcept）签名、阶段、根因均不同。
- ⚠ **E 号复用**：`knowledge/drafts/` 下 `E543-draft-` 前缀实测 52 份 `.kv`
  （含 `.md` 共 104 件），其中 `DRAFT-E543-ohos-conan-run-shell-quote-cstring`
  属完全不同机制 ⇒ 本台账与草稿一律**按文件名** `E543-draft-7707` 引用。
- `raise_t` / `eraise` 的 archives 命中面：`raise_t` 6 个文件全在
  `archives/j/jellyfish1/**` 自身；`eraise` 的其余命中是 `erase` 的**子串噪声**
  （crosstool-ng / gauche / gnustep-make / man-pages / openlibm / posixsignalmanager），
  非同一机制。

### 判据与路径判断（本条由 hit 升 create）

对照条目 `E543-draft-7707` 的**四条行号级层次差**：

1. `.md:28-30` 把 locus 划在「其测试**有意**验证析构抛异常」（libtut 的
   `teardown_ex` 组，`warn` 结果类型正是为该场景设计）；本包抛点在**被交付的库头**
   `jellyfish/err.hpp:123` 的 `~raise_t()`，是库全部错误抛出路径的唯一机制。
2. `.md:42-43` 断言「交付的库头文件在现代标准下正常（消费者代码不会故意从析构抛
   异常）」——本包该前提为假：消费者只要触发库内错误分支即 `std::terminate`、
   RC=134（`tc4-r2.out:23-25` 静态、`:40-42` 共享、`:52`/`:60` 加
   `noexcept(false)` 后 RC=0；GF(2) 随机矩阵奇异率约 29%）。
   该双臂探针同时**否证**了「cross-DSO RTTI/typeinfo」这一更省事的替代解释。
3. `.md:54-63` 的推荐解法（`-std=gnu++98` 重编上游套件、不改任何测试代码）在本包
   **不可用**：降档修不到交付库头；且同条 `:77-78` 自身禁止把 `gnu++98` 加进配方。
   ⇒ 本臂**只靠这两条独立成立的前提**（旧表述「自带 gtest 需 C++11」是未经证实的
   断言，已被同包一手读数否证并撤下）：自带 googletest 的实测障碍是
   `gtest-port.h:504` 在不定义 `GTEST_USE_OWN_TR1_TUPLE=1` 时走到
   `#include <tr1/tuple>`，而 libc++ 无 TR1 兼容层 ⇒
   `fatal error: 'tr1/tuple' file not found`（一手 `gtest-probe/without.log:4`）；
   处置是该编译期宏（A/B：不带宏单编 RC=1、带宏 RC=0，**未关闭 unit_tests 层** ——
   交付轮 `w3-local-ci.log:703` 真编 `libgtest_a-gtest-all.o`、`:710` `AR libgtest.a`、
   `:786 PASS: unit_tests/unit_tests.sh`）。该宏与 `-std` 无关（vendored 头内
   `GTEST_LANG_CXX11` 全域 0 命中），与本臂的降档出路是两条正交机制（见候选 4）。
4. `.md:73-74` 与 `.kv:34-36`（`forbid_1`）原文限定为「给上游**测试**的析构打
   `noexcept(false)` 补丁……套件本该用时代标准跑」；本包用的正是该形态，
   但落在该禁令**前提不成立**的场合。

⇒ **判据**：判 `hit` 的四条件之条件 2 ——「症状相同、但你用的是既有条目没写的
另一条解法时不算 hit，按 `create` 报」。**症状层**虽与 E543 同机制，
但**locus 与可用解法**都不在其覆盖面上（且其自划范围语句 `.md:42-43` 在本包为假）。
⇒ **新增价值一句话**：E543 的 `noexcept(false)` 禁令需要按 locus 收窄适用面——
抛点在测试套件时用时代标准重编（E543 原场景）；抛点在**被交付的库头**、
且降档标准被该条自禁时，`noexcept(false)` 一行才是最小干预正解。
⇒ 路径判断: **create**。本条**占用本 PR 的知识位**，交付物为成对草稿
`knowledge/drafts/DRAFT-jellyfish1-1.1.11-shipped-header-throwing-destructor-noexcept-false.{kv,md}`；
Issue 已由主理创建为 **#3405**（绝对链接与标题见 `1.1.11/notes.md` 的「关联 Issue」
一行）；本表与 notes 均已回填实号，**起草态占位已废除、不再出现**。

## 候选 2：profile 强推的 CONFIG_SHELL=bash 让 2013 autoconf/libtool 产出不可解析

- 真实错误: `./libtool: line 350: syntax error near unexpected token`（转义丢失）与
  `./libtool: line 907: print: command not found`（ECHO 被选成 toybox ash 内建的 `print`）
- 一手: `probe3-a.out:10`、`probe4-a.out:10` 均 `MAKE_RC=2`（导出 hnp bash 两臂）；
  `probe5b-a.out:8` `MAKE_RC=0`（不带 CONFIG_SHELL）；`probe-install.log` 6209 B
  全篇 0 条 error/Error 行 ⇒ make/install 腿成立
- 修复: `config.status` 内记录的 bash 路径整体改写为 `/bin/sh`，再以命令行前缀赋值
  `env CONFIG_SHELL=/bin/sh SHELL=/bin/sh /bin/sh ./config.status` 全量重生成 +
  `sh -n libtool` 自检（`conanfile.py:146-185` `_regen_build_outputs()`）
- 四范围查重: graph/doc 无；drafts 命中 `DRAFT-E551-ohos-conan-configshell-bash-libtool-escaping.md:1`、
  `:12-17`、`:25-28`（同签名同处置）；族谱对照
  `DRAFT-6487-classads-configshell-hmdfs-getcwd.kv:32-33`
- 路径判断: **reuse_existing（hit）**。解法与签名都被 E551 覆盖，症状层与处置层都命中；
  本包第二处故障（`ECHO=print`）与其共享同一根因与同一处置 ⇒ 按「组合型知识不判重」
  不单开。**不占本 PR 知识位。**

## 候选 3：libtool 产出的共享库不自动链接 compiler-rt builtins（`__udivti3`）

- 真实错误: `nm` 实拍 `U __udivti3` + 运行期
  `Error relocating .../libjellyfish-1.1.so.1: __udivti3: symbol not found`（exit 127）
- 一手: `probe8-a.out:3`、`:5-6`（塞 `libclang_rt.builtins.a` 后 configure 确认
  HAVE_INT128=1、make RC=0，`.so` 里仍 `U __udivti3`）、`:8` 运行期第一条错误、
  `:10` 冒烟产物未生成、`:11 CHECK_RC=2`、`:15-35`；probe8-check.log:33
  「19 of 19 tests failed」
- 处置: 配方钉 `ac_cv_type___int128=no`（走 divisor64 硬件除法分支）。本轮交付构型是
  `--disable-shared`（`reports/w3-local-ci.log:181` 的 configure 实拍行、
  `:259` shared no、`:260` static yes）⇒ 该面在交付物里不复现，
  但钉法对 `shared=True` 构型仍必要
- 四范围查重: drafts 命中 `DRAFT-libsidplayfp-2.15.1-compiler-rt-builtins-linking.kv:1`、
  `:8`（同族，符号由 `__powidf2` 换成 `__udivti3`）；其 `.md:51`
  「不命中：静态链接（.a）消费者」正对应本轮 `--disable-shared` 交付构型；
  同族另见 `DRAFT-13534-libzimg-3.0.6-libtool-nostdlib-builtins.md:20-23`
- 路径判断: **reuse_existing（hit）**。**不占本 PR 知识位。**

## 候选 4：源码树里 vendored 的 googletest 1.6 在 clang + libc++ 下编译失败

- 真实错误: `unit_tests/gtest/include/gtest/internal/gtest-port.h:504:13:
  fatal error: 'tr1/tuple' file not found`（单编 RC=1；带
  `-DGTEST_USE_OWN_TR1_TUPLE=1` RC=0，一手
  `~/tmp/uc2/z33-jellyfish1/gtest-probe/without.log:4`）
- 四范围查重: 全域（含 knowledge/drafts/）**0 命中** ⇒ 有独立成条资格
- 路径判断: **create 资格，但不占本 PR 知识位**（本 PR 的知识位已由候选 1 占用，
  一 PR 一知识）⇒ 草稿放配送池
  `~/tmp/uc2/z33-jellyfish1-bpool/DRAFT-jellyfish1-1.1.11-gtest-tr1-tuple-header-flags.{kv,md}`，
  由主理并入 `经验文档/B草稿库/`，本 PR 不含该知识点。

## 汇总

| 候选 | 判据结论 | 是否占本 PR 知识位 | 交付物 |
|---|---|---|---|
| 1 抛出析构在交付库头 | **create**（hit 四条件之条件 2 不满足） | **是** | `knowledge/drafts/DRAFT-jellyfish1-1.1.11-shipped-header-throwing-destructor-noexcept-false.{kv,md}` + Issue **#3405**（已回填） |
| 2 CONFIG_SHELL=bash | hit（E551） | 否 | 沿用池内条目 |
| 3 compiler-rt builtins / `__udivti3` | hit（libsidplayfp） | 否 | 沿用池内条目 |
| 4 vendored gtest `<tr1/tuple>` | create 资格（全域 0 命中） | 否 | 配送池件，不入本 PR |

本包对外 `适配路径` 三行 + Issue 一行的**唯一真值来源**是本表与
`1.1.11/notes.md` 的「适配路径」一节；两处口径必须一致。

## 落盘说明（交主理核）

- 本件路径 `archives/j/jellyfish1/1.1.11/reports/knowledge-candidate-ledger.md`
  被仓根 `.gitignore:96` 的 `reports/` 规则遮挡。既有先例（如
  `archives/b/brieflz/1.3.0/reports/knowledge-candidate-ledger.md`，`git ls-files`
  实测仓内共 20 份同名台账）都是**已纳入版本控制**的，故本件按先例以
  `git add -f -- <本件精确路径>` 单件纳入。
- **同包另外三份一手证据件已按主理裁定以 `git add -f` 一并纳入本 PR**：
  `reports/w3-local-ci.log`（61083 B，920 行）、`reports/conan-create.log`（4791 B）、
  `reports/conan-verify-report.md`（1402 B）。理由：`notes.md`、
  `test_package/MANIFEST.yml`、两级 `manifest.yaml`、`README.md`、本台账与两份草稿
  都按行号引用 `reports/w3-local-ci.log`，不带件则评审侧从 diff 无从复算
  （第 3 轮审计 R3-P2-2）。纳入前已按门禁口径自查这三份构建产物文本，逐条读数：
  凭证样式 0 命中（`token|passw|secret|bearer|api_key|BEGIN|eyJhbGci` 的唯一命中是
  `w3-local-ci.log:832` 安装清单里的头文件名 `token_ring.hpp`）；URL 面只有 conan
  中心仓 `center2.conan.io`（`:5`）、本包官方源 `.../jellyfish-1.1.11.tar.gz`（`:95`）
  与 conan 自身的 `file://` 预下载缓存行（`:97`、`:163`，属 predl 产物，路径里带上一
  个窗口的 worktree 目录名 `主理-33-jellyfish1-1.1.11`）⇒ 无 `deb.debian.org` 类禁用
  取源；模板占位串 0（`占位符` 只出现在它转述的 KC2 步骤名 `:48`/`:49`，而 KC2 的扫描面是
  `knowledge/graph/E*.kv`，不扫 `reports/`）；`:128`/`:147` 的 `26.0.0.18` 是 OHOS SDK
  版本号而非 IP。**如实披露一处先例里没有的形状**：`w3-local-ci.log:791` 含上游 CLI 自带
  的作者公开联系方式 `Please report to gmarcais@umd.edu`（抽查 raul/lutok/smtpping 三份
  已跟踪的同名日志均为 0 处邮件样式）——它是被交付软件自身输出的一部分，不是本仓人员的
  凭证或 PII ⇒ 按「⛔不改日志正文（那是改证据）」原样保留。三件在本轮纳入时的内容摘要
  （改前＝改后，逐字未动）：`w3-local-ci.log` sha256
  5fff98587d8253d2894889c89c09ef2af34b4e42eeb66f41b0fcf67ce4395529 / md5
  2d3711b6c5a0f23db66117eec8ffae42、`conan-create.log` sha256
  94645dbda206317551bd688b82e755bc7001c6893ca076718eadd942827e86f9、
  `conan-verify-report.md` sha256
  709c79069166f0b2deb633d1198ab5cce66a112557cb6580799758503e2654ce。
  按行号引用这三件的分布（本轮复测，`<file>:<行号>` 形式各计一处，共 **14** 处）：
  `w3-local-ci.log` 13 处 = notes 6 + 软件级 manifest 1 + README 1 +
  test_package/MANIFEST.yml 1 + 本台账 3 + 草稿 .md 1 + 草稿 .kv 1（其中 3 处是本轮
  整改新写）；`conan-create.log` 1 处、`conan-verify-report.md` 1 处（都在 notes 的
  「门禁与 preflight 实况」一节）。逐处行号都能在三件里读到且语义相符（三件行数
  920 / 99 / 48，越界引用 0；本段旧版本里 `w3-local-ci.log:<行号>` 那种零数字的
  写法不再存在）。
  与本包同批的仓内先例（当前 HEAD 实测跟踪件数）：`reports/w3-local-ci.log` 17 份、
  `reports/conan-create.log` 30 份、`reports/conan-verify-report.md` 167 份。
  ⇒ 本 PR 对 `reports/` 用 `-f` 的共 **4 件**（本台账 + 上述三份），再无其它 `-f`。
- 本轮所有改动均为非导出件与 `knowledge/drafts/`，不动配方导出面 ⇒
  recipe revision 不变，无需重跑 create/W3。
