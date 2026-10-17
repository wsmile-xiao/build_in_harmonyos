# DRAFT-ries-2018.08.05-self-reported-timing-field-in-byte-comparison — 消费者断言把被测程序自报的计时字段纳入逐字节比较 ⇒ 该稳定的输出"该不稳定"

> 状态：DRAFT（随 ries 2018.08.05 的 PR 提交，待人工/AI 复核后升 E 条目）。
> 本包一手读数全部随 PR：`archives/r/ries/2018.08.05/reports/assert9-det3/`、
> `archives/r/ries/2018.08.05/reports/assert9-fixcheck/`、`archives/r/ries/2018.08.05/reports/w3-local-ci.log`。

## 一句话机制

被测程序的**算法输出是确定的**，但它在收尾摘要里额外打印一枚**墙钟秒表**——
Ries 在 `print_end()` 里 `tsec = gettime()`（`ries.c:7511`），随后
`printf("  Time: %.3f\n", tsec)`（`ries.c:7540`，2018.08.05 钉版行号），
正常 CLI 用法下没有任何选项能单独关掉它（只有 `--find-expression` 一类非交互用法会经
`g_enable_output` 把整块统计一起抑制）。

于是"重复执行同一命令 ⇒ 输出逐字节一致"这条消费者断言**在原理上就不成立**：
机器越忙，该字段越容易落在不同的毫秒值上，断言越容易翻面。
**症状是随机假失败（flaky FAIL），不是硬失败，也不是上游/工具链/依赖缺陷。**

## 症状指纹（逐字，本包真件）

同树同机同 conan，18:42 那轮 9/9 通过，18:50 重跑变 8/9：

```
[test] FAIL -n3 output is byte-identical on re-run
[test] RIES_TEST_SUMMARY total=9 passed=8 failed=1
```

（原件：`reports/assert9-fixcheck/old4.log`，sha256 `a1482ac7a4185f3d…`；
同臂另外 5 轮 `old1/2/3/5/6.log` 均为 `total=9 passed=9 failed=0`，
sha256 同为 `d103f1193fb54661…` ⇒ 同一份脚本、同一臂，只有这一轮翻面。）

差异只落在 ries 输出第 13 行——**注意时钟与 dead-ends 三个计数在同一行**：

```
13c13
<           dead-ends:        2581         1907         4488  Time: 0.001
---
>           dead-ends:        2581         1907         4488  Time: 0.000
```

## 决定性证据：同一条命令 30 跑的两套 md5

`ries -n3 2.5063` 跑 30 次（B 机 aarch64），逐跑读数表随 PR：
`reports/assert9-det3/{times.txt, md_full.txt, md_mask.txt}`，取数脚本
`reports/assert9-det3/det3.sh`。可直接复算：

| 判据 | 实测 |
|---|---|
| 整份输出的 md5 种类 | **2 种**：`0ebaa69b1b` 23 次 / `0c29bb0b95` 7 次 |
| `Time:` 字段读值 | **2 种**：`0.001` 23 次 / `0.000` 7 次（与上一行逐次一一对应） |
| 掩掉该字段后的 md5 种类 | **1 种**：`aeefc3f5ed` ×30 |

⇒ 除该字段外的每一个字节（等式列表、`max complexity`、`dead-ends` 三个计数、
`expressions`、`distinct`、`Memory`、`Total equations tested`）在 30 跑里**全部恒定**。

再放一枚竞争 CPU 的进程连跑两次（`load_a.txt` / `load_b.txt`）：
原始 `cmp` rc=1（翻面），同一对文件掩掉该字段后 `cmp` rc=0（`la.txt` 与 `lb.txt` sha256
同为 `c3bdffa4115d65ab…`）。⇒ **机器越忙越容易翻面**，这正是两轮之间唯一的差别。

## 修法：字段级掩码 + 字段级正对照（两条闸门缺一不可）

```sh
# ① 主门禁：两臂各跑同一条字段级 sed（只吃掉 Time 冒号后的数字），再 cmp
sed -E 's/Time:[[:space:]]*[0-9][0-9.]*/Time: <elapsed>/' "$WORK/out9a.txt" > "$WORK/norm9a.txt"
sed -E 's/Time:[[:space:]]*[0-9][0-9.]*/Time: <elapsed>/' "$WORK/out9b.txt" > "$WORK/norm9b.txt"
cmp -s "$WORK/norm9a.txt" "$WORK/norm9b.txt"; norm_rc=$?
# ② 正对照：对同一对掩码后文本 diff，只允许 hunk 头与 --- 分隔行
diff "$WORK/norm9a.txt" "$WORK/norm9b.txt" \
  | grep -vE '^[0-9]+(,[0-9]+)?[acd][0-9]+(,[0-9]+)?$|^---$' > "$WORK/undisposed9.txt"
[ "$norm_rc" = "0" ] && [ ! -s "$WORK/undisposed9.txt" ]
```

要点是**字段级**：掩码只吃掉那一枚数字，正对照也在掩码后的文本上做。
本包第一版的正对照写成 `diff out9a out9b | grep -vE '…|Time: '`（**整行**丢弃含
`Time: ` 的行），实测强度低于声称强度——同一对文本在第 13 行同时改动
`dead-ends` 计数与 `Time` 值时：

| 正对照写法 | 未处置差异 | 结论 |
|---|---|---|
| 行级 `grep -vE '...|Time: '`（旧） | **0 字节** | 盲：非时钟差异被整行放过 |
| 字段级（本条，同一条 sed 后 diff） | **159 字节** | 抓到，且 `norm_rc=1` 同步失败 |

（对照读数出自 `reports/assert9-det3/` 同法构造的合成反例；改后的 `test.sh` 在
6 枚 spinner 负载下同臂实跑 4 轮，全部 `total=9 passed=9 failed=0`、rc=0。）

分母与断言条数**不变**（ries 仍是 9 条消费者用例）；改动只落在 `test_package/test.sh`，
不在 `export_sources` 内、不改 recipe revision。

## 禁止做法

1. ⛔ **用整行排除充当正对照**（`grep -vE '…|Time: '`）：被测程序常把时钟与别的计数
   印在同一行，行级排除会连非时钟差异一起放过。
2. ⛔ **靠缩小比较面凑绿**（删掉 `dead-ends`/`Memory`/计数行、只比前 N 行、只比等式列表）：
   这条断言的价值恰恰是验证**全部**统计恒定。只掩确实随机的那一枚字段。
3. ⛔ **删掉整条断言 / `|| true` 吞 rc / `ignore_errors` / 整条 SKIP**：也禁止把
   "随机"直接定性成 OHOS、工具链、依赖或上游缺陷——没有 30 跑两套 md5 这类读数就不许定性。

## 适用面 / 反例

- 适用：任何"重跑同一命令并逐字节比对两次输出"的消费者断言，且被测程序会在正常输出里
  打印自报耗时/秒表/时间戳（`Time`、`elapsed`、`took`、`seconds`、`CPU time`、
  `Duration`，或任何 `time`/`gettimeofday`/`clock_gettime` 的结果被 `printf` 进输出）；
  高发形态是求解器、编译器基准、"跑完打印统计"的 CLI 工具。
- 不适用：输出完全确定（无时钟字段）却仍翻面 ⇒ 先查 harness 落点与 env 三臂
  （下一节），不要引本条。

## 判重结论与层次差（create 的三条对齐行号）

**create**。四范围检索读数见
`archives/r/ries/2018.08.05/reports/knowledge-candidate-ledger.md` 的候选 3 节：
`knowledge/graph|doc|operations` 上三档词集**有字面命中但机制级命中 0**——
A 组（`stopwatch`/`elapsed time`/`wall.clock`/`clock_gettime`/`non-determinis`）25 条，
逐条核对是**时钟源可用性**（`E152.kv:4,12`、`E270.kv:8,12,17,30`）；
B 组（`逐字节`/`秒表`/`计时字段`/`墙钟`/`随机失败`/`flaky`）23 条，最近邻 `E057.kv:8,13,16,19,23`
是 regrtest 开满 worker 造成的**真**不确定（解法 `env-var-override`），`E488.kv:40,70` 的
"逐字节"是 HMDFS 上重写 `.so` 的手法，`E528.kv:35`/`E330.kv:39` 的 flaky 只出现在
`forbid_*_reason` 里；C 组（`Time:` 加空格）2 条是 `E537.kv:45`/`E537.md:36` 散文
`at link time:` 的字面假阳性。`knowledge/drafts/` 手工 grep 的命中件全在不同层
（`DRAFT-9995-f3d-vtk-gles-egl-upstream-tests.kv:39,55` 是 `GL_TIME_ELAPSED` 常量名、
`DRAFT-8425-*.kv:9,14` 是产物等价源判定、`DRAFT-8959-*.kv:33` 与 `.md:52,60` 是移植义务、
`DRAFT-9200-lddtree-shell-tool-portability.kv:57` 是不许改上游测试件、
`DRAFT-8543-*.kv:19,56`/`DRAFT-E577-*.kv:47`/`DRAFT-E616-*.md:92,95` 是产物字节对照、
`DRAFT-10686-*.kv:42`/`E558-draft-7899.kv:78`/`E544-draft-A7F3.kv:16,27`/`E430-draft-7707.kv:42`
是取时路径与符号可用性）。`scripts|ci|docs` 0 命中；池内 `B草稿库` 对 A 组与
`逐字节|byte-identical|cmp -s` 均 0 命中，最近邻 M15 方向相反。
**上表全部行号已由 `verify-anchors.py` 逐条实读复核（TOTAL_FAILS=0）。**

1. 池内最近邻 **M15**（`经验文档/B草稿库/DRAFT-PKG-VER-hishell-swallows-sigalrm.kv`
   的 `:7` title、`:10` error_signature、`:16` root_cause、`:41` rec_description，
   池索引行 `README.md:31`）**方向相反**：
   M15 = 上游用信号实现超时被 hishell 吞掉 ⇒ **该失败的没失败**（假通过 + 少报超时）；
   本条 = 被测程序自报耗时进了逐字节比较 ⇒ **该稳定的不稳定**（假失败）。
2. 本仓既有两族口径讲的是 **harness 落点/环境**："同一 test.sh 原生全绿而 conan 下差 1 条
   ⇒ 先查 CWD / 两臂输入字节 / env 三臂"、"L1e 把参考输出相对写到 cwd 被负照轮覆写"。
   本条差异来源在**被测程序自身的 printf**，双臂同臂、同 cwd、同 env 也必然翻面。
   Ries 本包的排除顺序正是先按三臂口径否证环境说（`test_package/` 下无残留 ⇒ 未触发
   `mkdir` 失败的 `WORK=.` 回退；`conanrun.sh` 同臂 6 轮对照）才落到时钟说
   ⇒ 两条是互补的排查顺序，不是同一条知识。
3. 同包另一面 `make install` 缺 `install(1)` 按 **E174** 记为 `hit` 引用
   （`knowledge/graph/E174.kv:5,13,17,22-23`），按文件名引用、不占本条知识位。

## 诚实边界

- 本条只覆盖"时钟字段进逐字节比较"这一层；`Memory`/`Total equations tested` 留在比较面内
  是**有意不放宽**，本机 30 跑恒定，**原则上仍属环境敏感**，换机/换内存布局可能翻面，
  届时同样按本条口径处理（先取逐跑读数，再决定掩哪一枚）。
- 修法是 harness 改写，未验证"该字段可被上游选项关掉"的路线（ries 无此选项）。
- 申报前必须自己留下"全量 md5 多种 / 掩码后一种"的逐跑表与加负载两跑对照，
  否则无法与"落点被覆写""env 三臂不一致"区分。
