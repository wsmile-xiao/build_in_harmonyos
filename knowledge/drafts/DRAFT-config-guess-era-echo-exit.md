# DRAFT-config-guess-era-echo-exit — 2006/07 年代 config.guess 无统一尾部输出结构，E007 的 GUESS= 变量式补救注入后不生效仍报 unable to guess，须改用 echo+exit 旧式分支

> **Contributor**: GoliWie | **Status**: DRAFT（最终编号由知识库主编确认） | **Updated**: 2026-09-04
> **Severity**: blocking (2) | **Category**: autotools / config.guess / ohos / patch
> **Audience**: 在 OHOS 上适配带年代版 config.guess/config.sub 的 autotools 老项目、维护或使用 E007 补救脚本的配方维护者

## 触发（trigger）

- 上游 tarball 自带 **2006–2008 年代** config.guess（libmirage/cdemu-daemon 1.0.0 为
  2006-07-02 版，timestamp 行可证）。
- 已按 E007 标准方案打补丁（`scripts/patch-autotools-ohos.pl`，其注入分支为
  **GUESS= 变量式**，见 pl:51-63），随后运行 configure。
- configure 在 config.guess 步骤失败——**尽管补丁已在**。

## 症状（symptom）

```
config.guess: unable to guess system type
...
config.guess timestamp = 2006-07-02
UNAME_MACHINE = aarch64
UNAME_SYSTEM  = HarmonyOS
...
rc=1, stdout 为空
```

签名本体落回 E007 的 `unable to guess system type`；**本条的诊断增量**是
"已打补丁仍失败"这一入口：脚本内已含 HarmonyOS 分支（或 `grep -c 'GUESS=' > 0`）
却仍报同横幅 = 代际形态不匹配，而非补丁未打。失败是**响亮**的（stderr 横幅 +
exit 1 + 空 stdout）；"拿到空三元组"仅在调用方同时吞 stderr 且忽略退出码时出现
（边注——不要把它当成静默失败来排查）。

## 机制（root cause）

1. **该代脚本没有统一尾部输出结构**：主 `case` 的各分支自行
   `echo <三元组>` + `exit ;;`；`GUESS` 变量在脚本内**零处出现**，也不存在现代脚本
   "全程只赋值 GUESS、脚本尾部统一 echo $GUESS" 的出口。
2. **E007 官方补救是现代形态**：`scripts/patch-autotools-ohos.pl:51-63` 注入的
   HarmonyOS 分支为 `GUESS=${MACHINE}-unknown-linux-ohos` + `;;`——在年代脚本上
   **只赋值不输出**；控制流越出 case 进入 LIBC/dummy.c 探测段，最终到达脚本尾部
   "unable to guess system type" 横幅 + exit 1 + 空 stdout（三态实验 STATE_G 独立复现）。
3. 正确形态是沿用该代的分支自足约定：**echo + exit**（先例：libdaemon 0.14 补丁
   0001；libmirage 1.0.0 补丁 0001 同型）。

## verification_cmd（三态对照，自包含）

```sh
# 前提：任一年代 config.guess，guard：grep -c 'GUESS=' 与 grep -c HarmonyOS 均须为 0
#（以 pristine 树顶层脚本为例；timestamp 行应早于 2010）
D=$(mktemp -d) && cd $D
CG=<pristine>/config.guess
grep -c 'GUESS=' $CG; grep -c HarmonyOS $CG
cp $CG cg
L=$(grep -n -m1 -E '^[[:space:]]*\*:NetBSD' cg | cut -d: -f1)
printf '%s\n' '    *:HarmonyOS:*:*)' '	MACHINE="$UNAME_MACHINE"' '	GUESS=${MACHINE}-unknown-linux-ohos' '	;;' '' > inj_g
printf '%s\n' '    *:HarmonyOS:*:*)' '	echo aarch64-unknown-linux-ohos' '	exit ;;' '' > inj_e
head -n $((L-1)) cg > cg.g && cat inj_g >> cg.g && tail -n +$L cg >> cg.g
head -n $((L-1)) cg > cg.e && cat inj_e >> cg.e && tail -n +$L cg >> cg.e
sh cg  >o.out 2>o.err; echo "rc=$? stdout_bytes=$(wc -c <o.out)"; grep -m1 "unable to guess" o.err
sh cg.g >g.out 2>g.err; echo "rc=$? stdout_bytes=$(wc -c <g.out)"; grep -m1 "unable to guess" g.err
sh cg.e >e.out 2>e.err; echo "rc=$?"; echo "stdout: $(cat e.out)"
rm -rf $D
```

逐字实跑输出（2026-09-04 补证轮；libmirage pristine 树脚本 timestamp=2006-07-02、
GUESS==0、HarmonyOS==0、NetBSD@145；注入行内为真实 Tab）：

```
0
0
rc=1 stdout_bytes=0
cg: unable to guess system type
rc=1 stdout_bytes=0
cg.g: unable to guess system type
rc=0
stdout: aarch64-unknown-linux-ohos
```

三态读法：era 原脚本失败（基线）→ **GUESS= 注入仍失败（补救不生效实证）** →
echo+exit 注入输出三元组 rc=0（正确形态）。

## 修复（rec）

在主 case 顶部（惯用插在 `*:NetBSD:*:*)` 分支前）注入 **echo+exit 形式** 的
HarmonyOS 分支；config.sub 参与构建时同步两处白名单（KERNEL-OS 组合的
`linux-ohos*`、OS 列表的 `-ohos*`）：

```sh
L=$(grep -n -m1 -E '^[[:space:]]*\*:NetBSD' config.guess | cut -d: -f1) && head -n $((L-1)) config.guess > cg.new && printf '%s\n' '    *:HarmonyOS:*:*)' '	case "$UNAME_MACHINE" in' '	    aarch64|arm64) MACHINE=aarch64 ;;' '	esac' '	echo ${MACHINE}-unknown-linux-ohos' '	exit ;;' '' >> cg.new && tail -n +$L config.guess >> cg.new && mv cg.new config.guess && sh config.guess
```

注意与本仓姊妹草稿 DRAFT-bison-pure-parser-yylex-signature 相互独立（不同机理）；
与 E007 面向现代脚本的 GUESS= 形态**按脚本代际二选一**（判据 `grep -c 'GUESS='`）。

## fallback（退路，含诚实权衡）

**replace-with-modern-gnuconfig**：用现代 GNU config 脚本（automake 捆绑/
gnuconfig 资产）整体替换年代脚本——现代脚本有统一尾部输出（GUESS= + 尾部 echo），
E007 现代补救形态即可生效。诚实权衡：uname 处理、libc 探测分支随代际漂移，替换后
必须复跑核验三元组与全量 configure，不能只看 config.guess 单点通过。

## 禁忌（forbid）

1. `--build/--host` 绕过系统检测（P-AUTOTOOLS-001 铁律）：鸿蒙是原生编译环境，
   绕过 → cross_compiling=yes → AC_RUN_IFELSE 跳过 → config.h 错误。
2. 对年代脚本套用现代 GUESS= 式注入并假定生效（**含 E007 官方 perl 脚本
   patch-autotools-ohos.pl:51-63 的注入形态——三态实验实测失效**）。
3. 吞 stderr / 忽略退出码，把响亮失败误读为"空三元组"——丢掉唯一诊断线索。

## 查重（dedup）

- E007：覆盖"config.guess/sub 不识别 linux-ohos，需打补丁"及 modern 形态补救；
  其全文无代际输出结构论述，且官方 rec（GUESS= 式注入）在目标场景（年代脚本）
  实测失效。本条增量：(a) "已打补丁仍失败"的判别特征（脚本含 HarmonyOS 分支/
  GUESS=>0 却仍 banner）与诊断入口；(b) echo+exit 旧式分支的正确形态与三态对照法；
  (c) E007 修订诉求（见下）。knowledge/graph 与 knowledge/drafts 检索
  （config.guess/echo+exit/GUESS=/era/ unable to guess）无既有条目覆盖此增量。

## E007 修订诉求（随本条并行提交主编）

建议在 E007 的 rec_description / rec_command 增加时代前置条件：

> "§GUESS= 注入形态仅适用于含统一尾部输出（分支只赋值 `GUESS=`、脚本尾部统一
> `echo $GUESS`）的现代脚本；timestamp 早于约 2008 的脚本（判据
> `grep -c 'GUESS=' == 0`）必须改用 echo+exit 旧式分支（echo <三元组> + `exit ;;`
> 注入到主 case，见 DRAFT-config-guess-era-echo-exit 的三态验证）。"

并请在知识库 doc/ 内固化事实锚点：E007 官方 `scripts/patch-autotools-ohos.pl`
注入形态位于该脚本 **51-63 行**（GUESS= 式、无 echo/exit）——该脚本目前仅存在于
临时 ci-logs worktree（xorgproto-2024.1-30145784e9ba），非稳定资产路径，修订落地时
应把行号事实与形态描述一并固化进 doc/。若主编终裁并入 E007 而非独立成条：本条
三态验证与 forbid 2/3 可直接并入，B 判定仍以单条成立，A+B 结论不变。

## 证据（evidence）

- pristine 脚本：/storage/Users/currentUser/tmp/builds/libmirage-1.0.0.orig/config.guess
  （tarball 原样解包，mtime 2007-12-20；timestamp=2006-07-02；GUESS==0；HarmonyOS==0；
  NetBSD@145）。
- E007 官方注入形态：scripts/patch-autotools-ohos.pl:51-63（GUESS= 式、无 echo/exit）。
- 同型先例：libdaemon 0.14 patches/0001-config.guess.patch（echo+exit 形式）；
  libmirage 1.0.0 patches/0001-config-guess.patch 同型。
- 补救不生效的构建现场：libmirage-1.0.0 run 构建序列 lm-create-1（E007 补丁后
  configure 仍失败于 config.guess，后经定位注入形态才闭环）。

## 关系（relations）

- principles: P-AUTOTOOLS-001, P-PATCH-001
- similar_to: E007
- prerequisite_of: 无；conflicts_with: 无
