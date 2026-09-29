# skewer 0.2.2：EOF 负返回值被调用侧当成错误分支，静默丢弃整块记录（奇偶相关的丢数据）

> 说明：本文件对应 `.kv` 同 stem 草稿 `DRAFT-skewer-0.2.2-eof-negative-return-discarded-block`。

## 场景

skewer 0.2.2（NGS reads adapter 修剪工具，裸 Makefile，C++）适配 HarmonyOS PC。上游无测试，消费者测试用真实 FASTQ 输入跑二进制并断言输出记录数。首轮交付时观察到一条**与输入条数奇偶相关**的行为：偶数条正常、奇数条**少处理最后一条**，且过程**无任何报错**（rc=0）。

## 现象（全部真机原文）

编译期告警（clang 15，OHOS SDK 26.0.0.18）：

```text
src/fastq.cpp:87:9: warning: result of comparison of constant -1 with expression of type 'char' is always false [-Wtautological-constant-out-of-range-compare]
        if(tag == EOF)
src/fastq.cpp:96:24: warning: result of comparison of constant -1 with expression of type 'char' is always true [-Wtautological-constant-out-of-range-compare]
                while (c != '>' && c != EOF) {
```

运行期定量判决（同一组 fixture，`/storage/Users/currentUser/tmp/uc2/z63-skewer-fix/`）：

```text
修复前  before-odd-count.log   VERDICT N=5 : input=5 output=4 rc=0 malformed=2   （只处理 4 条，止于 @read4）
修复前  before-odd-count.log   VERDICT N=8 : input=8 output=8 rc=0 malformed=2
修复后  after-odd-count.log    VERDICT N=5 : input=5 output=5 rc=0 malformed=0
修复后  after-odd-count.log    VERDICT N=8 : input=8 output=8 rc=0 malformed=0   （42bp 剪切位点无回归）
符号性  charmin-probe.out      CHAR_MIN=0 CHAR_MAX=255   (char)(-1) as int = 255
反向    a10-negative-control.log  [FAIL] A10 奇数条记录被丢弃（EOF 哨兵缺陷复发） — rc=0 in=5 out=4 ⇒ 9/10 passed（断言非恒真）
```

## 根因（两层，缺一层都解释不了"奇偶相关"）

1. **语言层（已知家族）**：C 允许 plain `char` 的符号性由实现决定。OHOS 目标 `clang -dumpmachine` = `aarch64-unknown-linux-ohos`，实测 `limits.h` 的 `CHAR_MIN == 0`、预定义 `__CHAR_UNSIGNED__` ⇒ `fgetc()` 返回的 `EOF(-1)` 存入 `char` 后变成 `255`，`c == EOF` 永不成立。落点：`src/fastq.h:91` 的成员 `cFQ::tag` 与 `src/fastq.cpp:93` 的局部 `c`，共覆盖 `:87`、`:96`、`:104` 三条死比较（全树 `fgetc|getc|getchar` 只有 4 处命中，都在 `cFQ::readRecord()` 内；另一处 `char chr` 不是 EOF 接收者，不改）。
2. **调用语义层（本条新增价值）**：`cFQ::readRecord()` 在 EOF 时返回的是 **`-2`**（不是 `-1`）。调用侧 `main.cpp:936-940` 写的是 `if (rc < -1) continue;`，即把"读到文件尾"当成"这一批出错了"，于是**丢弃该批已读记录**。批大小 = `nBasicSize * n_threads`，而 `nBasicSize = (len > 800MB) ? 10 : (len / 100MB + 2)` ⇒ **对 KB/MB 级输入 `nBasicSize` 恒为 2** ⇒ 奇数条时最后一批只有 1 条，撞上 EOF 就被整批丢掉；偶数条恰好不掉。这就是"只有奇数少一条、而且 rc=0 无报错"的完整机制。

⚠ 只写第 1 层会漏掉判据要点：**同一个 char/EOF 缺陷在不同调用方语义下外显完全不同**（挂起 / 死循环 / 静默丢数据 / 丢一整块），所以处置时不能只把 `char` 改 `int` 就收工，必须回看调用侧如何解释 reader 的负返回值。

## 修复

最小补丁 `archives/s/skewer/0.2.2/patches/0001-fix-char-eof-sentinel.patch`（`patch_type: portability`，sha256 `74803cdfd9739b3454049f0c76ff1c2fafddf3202825de286375c3cff9791fb2`；`patch -p1` 与 `patch_ng.apply(strip=0)` 均通过，`diff -r` 只两文件各一行）：

```c
-    char tag;            /* src/fastq.h:91  cFQ::tag  */
+    int  tag;
-        char c;          /* src/fastq.cpp:93 readRecord() 内局部 c  */
+        int  c;
```

`conanfile.py` 原本已有 `export_sources()` 与 `build()` 里的 `apply_conandata_patches(self)`，无需新增调用。补丁**不带平台特判**（任何 plain-char-unsigned 目标都需要它），故文件名不带 `-ohos` 后缀，避免误导评审。

## 验证（可复算）

```sh
# 1) 符号性依据（含 limits.h 的探针文件）
clang -dM -E probe.c | grep -i CHAR_UNSIGNED ; printf '%d %d\n' CHAR_MIN CHAR_MAX
# 2) 判据本身：奇数条与偶数条各跑一次，比对输入/输出记录数与 malformed 计数
sh test_skewer.sh <package_folder>/bin/skewer <scratch>       # A9 偶数(8) + A10 奇数(5) 回归断言
# 3) 反向验证：最终版脚本打**未打补丁**的旧产物 ⇒ A10 必须转红（9/10, rc=1）
```

W3 阻塞门禁在最终树复验：`python3 scripts/ohc-run.py conan-verify skewer 0.2.2` ⇒ `G1/G2/G3 PASS`、`Verdict: PASS`；create 日志含 `Building from source` 与 `Apply patch (portability)`（非 cache 命中的绿）。消费者测试 `HMBS_TEST_PACKAGE_RESULT`：`discovered:10 passedCount:10 failedCount:0 skippedCount:0`。上游静态测试数 0（三条实测证据，非"平台没环境"）。

## 适用边界

- **适用**：上游 reader（`fgetc/getc/getchar/scanf/%c`、或自定义 `readXxx()` 用负值表示 EOF/结束）的返回值接收变量声明为 plain `char`，且**调用方对负返回值另有分支语义**（`rc < -1`、`rc == -2`、`rc < 0 即错误` 等）。典型面：手写词法/数值扫描器、FASTQ/FASTA/C SV/日志解析器、行读取回退路径、批处理流式解析器。
- **不适用 / 别照抄**：若调用方只认一个错误码且 EOF 走正常出口，症状会是**死循环或超时**（那就是 `DRAFT-8543-plain-char-eof-sentinel-infinite-loop` 的形态，处置只需 widen 接收变量）；若 reader 返回 `size_t`/计数而非负哨兵，本条不适用。
- **反例提醒**：不要把本条误用成"所有 char 都要改 int"——只改 **EOF/负哨兵的接收变量**。skewer 全树另一处 `char chr` 不承载 EOF，实测不改（改了会引入无关 diff）。
- **判据要点**：奇偶/边界条数对照是**最便宜的复现法**（比读透调用方快）；但只证"会丢"，要定量还得算清批大小公式里的常量（本包 `nBasicSize` 在 <100MB 时恒为 2，是"奇数才掉尾"的直接原因）。
- **未覆盖（如实申报）**：≥100MB 输入与多线程（丢 `1..block-1` 条）未实测；本包 `fastq.cpp:93` 那处属 FASTA 读取分支，只有编译器判决与类型推理支撑，无运行期正反例；gzip 输入输出路径与 `build_type=Debug` 变体未测。

## 查重

| 既有条目 | 关系 | 差异要点 |
|---|---|---|
| `DRAFT-8543-plain-char-eof-sentinel-infinite-loop`（severity 3，looktxt 1.4.1） | **同根因，不同外显与处置面** | 那条：`do-while (c != EOF)` 是唯一出口 ⇒ 循环无退出 ⇒ 100% CPU / 超时 `rc=124`，且 stderr 被 `shell-init` 污染；本条：EOF 经 reader 转成 `-2`，被调用侧 `rc < -1` 判成错误分支 ⇒ **静默丢弃整块已读记录**（rc=0、无报错、奇偶相关），处置必须多查一层调用方对负返回值的语义 |
| `E419`（plain char 作有符号 8 位样本，INT8 API 数值差 256） | 同源于实现定义行为，症状与处置均不同 | 那条数据仍在、只是数值错；本条是控制流/错误路径被误触发导致数据消失 |
| `DRAFT-cohomcalg-0.32-makefile-gxx-override` / `E053` | 无关（本包另一处卡点） | 本包 `make: g++: No such file or directory` 属**变量赋值型**，命令行 `make CXX=<clang++>` 实测即可覆写，与"编译器名写在规则命令位字面量"那一型（jnoise #12561）不同，已按 hit 处理不进本草稿 |

新增价值一句话：**给"char/EOF 家族"补上第二档外显——EOF 被调用侧当成错误码 ⇒ 按批静默丢数据**，并给出最省事的复现判据（奇偶条数对照）与"改完类型必须回看调用侧负返回值分支"的处置要求。
