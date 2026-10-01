# DRAFT-kma-1.4.21-unconditional-sysv-probe-makes-upstream-file-fallback-unreachable-and-wall-is-per-subcommand

> **本条只写组合层两件事**：① 上游"探测在前、else 兜底在后"的自愈分支在本平台
> **永不可达**（被拦的 shmget 是**终止型**失败，根本不返回，`if (shmid < 0)` 因此从不求值）；
> ② 同一道 seccomp 能力墙在一份产物里**按子命令分面**，故可用面/不可用面必须逐子命令成表。
> 机制层（"OHOS 用 seccomp-BPF 按 syscall 号把 SysV IPC 拦成 SIGSYS"）归池内既有条目
> `knowledge/drafts/DRAFT-ohos-sysv-shmget-sigsys.md`，本条**不重复申报**，
> 该条目「可复用修复模式」只给了两条解法——第 36-38 行的**编译期** mmap 开关
> （`fallback_approach: compile-time-mmap-switch`，如 AFL++ 的 `TEST_MMAP=1` → `-DUSEMMAP=1`）
> 与第 39-45 行的手工重写 `setup_shm()`/`remove_shm()` 换 POSIX shm。本包**零补丁、不换后端**，
> 用的是上游自带的**运行期 argv 开关** `-mmap`（`kma.c:525` 原文
> `else if(strcmp(argv[args], "-mmap") == 0 || strcmp(argv[args], "-swap") == 0)`，
> :526 置 `shm |= 32`、:527 换 `hashMapKMA_munmap`；同一行的右半支 `-swap` 与 `-mmap` 命中同一分支、
> 效果相同 ⇒ 解法面要读作「上游自带的运行期开关 `-mmap`（同义别名 `-swap`）」）⇒ 这是那两条都没写的**第三条解法**，
> 按 `经验文档/手册/03-路径B与C.md:83`（既有条目没写的另一条解法 ⇒ 按 create 报）计入本条新增面。

## 一、上游自愈为什么不可达（新事实）

`hashmapkma.c` 的 `hashMapKMA_load()`（:275 起）在四处用同一形状探测共享内存段：

| 位置 | 探测 | 兜底判定 |
|---|---|---|
| :319 / :320 / :321 | `key = ftok(filename, 'e');` | `shmid = shmget(key, size, 0666);` 之后才 `if (shmid < 0)` |
| :349 / :350 / :351 | 同型（`'v'`） | 同型 |
| :385 / :386 / :387 | 同型（`'k'`） | 同型 |
| :416 / :417 / :418 | 同型（`'i'`） | 同型 |

关键点不是"shmget 被拦"，而是 **兜底的进入条件是 shmget 的返回值**：本平台 shmget 命中
seccomp-BPF 的 `SECCOMP_RET_TRAP` ⇒ 信号在**返回之前**就到 ⇒ `if (shmid < 0)` 一生不被求值
⇒ 那一段"普通文件读"的 else 分支**永不可达**。真机表现即默认比对 `rc=159`
（128+31=SIGSYS）且 `out_default.res/.aln/.fsa/.frag.gz` 四件全 **0 字节**（写都没开始）。

**上游自己知道这个形状需要桩化**——同一文件 `hashmapkma.c:27-36`：

```c
#ifdef _WIN32
typedef int key_t;
#define ftok(charPtr, integer) (0)
#define shmget(key, size, permission) ((size != 0) ? (-1) : (-key))
#define shmat(shmid, NULL_Ptr, integer) (NULL)
#else
#include <sys/ipc.h>
#include <sys/shm.h>
#endif
```

Windows 走"恒失败宏"，探测**返回** -1 ⇒ 文件兜底可达；OHOS 目标
（`aarch64-unknown-linux-ohos`，`_WIN32` 未定义）落进 `#else` 的真实声明，**没有这层桩**。
⇒ 同一份源码在一种平台上自愈、在另一种平台上是终止型失败。

**判据（可复用）**：读上游"看起来能救命"的兜底时，先问它的进入条件是**被拦调用的返回值**
还是**被拦调用本身**。前者兜底可达（照常披露即可），后者在 SECCOMP_RET_TRAP/KILL 下恒不可达
⇒ **不得把"上游有 else"当成退路**，也不得因此免做能力披露。
（附一条禁忌：本平台**不要**为绿灯私自打开 `_WIN32` 桩宏——那会让 `kma shm`/`kma db`
"假装没有段"而改变上游语义；它在这里只是判据与 Issue 素材。）

## 二、同一道墙按子命令分面（新事实）

`grep -rl "shm & 32"`（`-mmap` 的运行期开关位）在 64 个 .c 里**只命中两个文件**：

```
kmers.c      # :85 hashMapKMA_load_shm / :86-87 else if(shm & 32) → hashMapKMAmmap / :89 默认路径
sparse.c     # :380 hashMapKMA_load_shm / :381-382 else if(shm & 32) → kmmap.c:33 hashMapKMAmmap / :384 默认路径
```

于是**同一份 `bin/kma`** 里出现三个面（全部真机实测，2026-09-25 B 机）：

| 子命令 | 本平台状态 | 依据 |
|---|---|---|
| `kma map`（`kma -i q -t_db db -o out`） | 默认路径**不可用** rc=159、四件输出全 0 字节；带 `-mmap` **可用** rc=0 且数值与上游语义一致（`t1 / Score 300 / Template_length 600 / Template_Coverage 50.00 / Query_Identity 100.00 / Query_Coverage 200.00`） | sparse.c:381-382 / :384、kmers.c:86-87 / :89、kmmap.c:33、kma.c:525-527（置 `shm \|= 32`，同行右半支 `-swap` 与 `-mmap` 同支同效） |
| `kma db` | **整条不可用** rc=159 —— db.c 里没有 `shm & 32` 分支 | db.c:59 直连 `hashMapKMA_load` |
| `kma shm`（含 `-destroy`） | **整条不可用** rc=159 —— 定义上就是 SysV 段的装/卸 | shm.c（全树唯一 `IPC_CREAT` 建立方）、main.c:57-58 |
| `kma index` / `kma dist` / `kma trim` / `kma seq2fasta` / `kma -v` / `kma -h` | 可用（rc=0，各有产物读数；`kma index` 产出 `testdb.comp.b` 4208420 字节） | 不经 SysV 哈希表加载 |
| `kma update` | **未测**：无参 rc=0 只回 `Insuffient amount of arguments handed!!!`；`update -i <fa>` rc=1 报 `Invalid option: -i`；未试出正确用法 ⇒ 无功能读数，既不列可用也不列不可用 | `~/tmp/uc2/z33-kma-fix2/up2-bare.log:2`（`rc=0`，`:4` 为 usage 原文）、`~/tmp/uc2/z33-kma-fix2/up2-i.log:2`（`rc=1`，`:4` 为 `Invalid option:`）；更早的旧两件 `~/tmp/uc2/z33-kma-fix/up-bare.log`（41 字节）、`up-i.log`（338 字节）只落 stdout、全件内无 `rc=` 行 ⇒ 那两个 rc 当时缺一手载体 |

**判据（可复用）**：多子命令 CLI 的能力面必须**逐子命令点名并各给依据行号**，
写"本包可用/不可用"必然失真——同一条墙下，有的子命令有可达出路、有的一辈子没有。

## 三、条目外偏差（提请修正池内条目，本条不代改）

池内 `knowledge/drafts/DRAFT-ohos-sysv-shmget-sigsys.md`「根因」节写"拦截
`shmget`/`shmat`/**`shmctl`**"。两个不同包的独立探针实测都否证了 `shmctl` 那半句：

| 号 | kma 1.4.21（`~/tmp/uc2/z33-kma/probe-summary.txt`） | radioclk 1.0.pristine（`~/tmp/uc2/z33-radioclk/shm-probe-run3.log`） |
|---|---|---|
| `shmget`/`shmat`/`shmdt`/`msgget`/`msgsnd`/`msgrcv`/`semget`/`semop`（八号，照一手件原序） | SIGSYS（si_code=1 SYS_SECCOMP，八号全部，`~/tmp/uc2/z33-kma/probe-summary.txt:5`） | SIGSYS（该件实测只覆盖其中 `shmget`/`shmat`/`shmdt`/`msgget`/`semget` 五号，`msgsnd`/`msgrcv`/`semop` 不在此探针内） |
| `shmctl` / `msgctl` / `semctl` | **进内核返 EINVAL(22) = 放行** | **返 EINVAL(22) = 放行**（`shmctl(SHM_INFO)` 返 0，`used_ids=0 shm_tot=0`） |
| `ftok` | **放行**（返 key） | **放行**（16797236） |
| 对照 `malloc` / 文件 `mmap`+`msync` / `shm_open`+`ftruncate`+`mmap` | 全通过 | 全通过 |

⇒ 建议该条目把拦截面改成"**创建/挂接类被拦、控制类 `*ctl` 放行**"。本条只提请、不代改他人条目。

**另一处提请裁定（池内三件互斥，本条不代改、不代定性）**：
`DRAFT-E584-bus-sysv-ipc-sigsys-catchable.md` 第 1 行标题与第 28-29 行称该 SIGSYS **可捕获**
（`sigaction` + `sigsetjmp`/`siglongjmp` 可捕获并继续执行）；而 `DRAFT-ohos-sysv-shmget-sigsys.md`
第 47 行称「OHOS 对部分被拦 syscall 的 SIGSYS 不可捕获，方案无效」、
`DRAFT-E577-buffer-sysv-ipc-posix.md` 第 36 行称「signal handler | 可捕获 | 本族 syscall 的 SIGSYS
通常不可恢复」。三处措辞互相排斥 ⇒ 提请条目所有者按包 / 按 syscall 号裁定可捕获性的真实边界。
本包一手读数只支持一句：默认比对路径命中 `shmget` 后进程以 `rc=159` 终止、`out_default.*` 四件全
0 字节（该进程未捕获该信号、未续跑）⇒ 本条把判据建立在「**探测不返回因而 else 判定一生不被求值**」
这一实测事实面上，不援引任何一方的可捕获性结论。

## 四、边界与禁忌

- ⚠ **策略相对性**：读数出自 HongMeng Kernel 1.12.0 / OHOS SDK 26.0.0.18 / musl、
  sshd→toybox sh 派生进程域、B 机。换版本或换启动域**必须重跑探针**，不得沿用本表。
- ⛔ 判能力用**真实 syscall**（fork-per-test + 同树对照组），禁 `stat()`/`/dev/shm`/符号表推断。
- ⛔ SIGSYS 只记在**实际发出的那个号**上（本包默认路径归 shmget，不得写"ftok 也被拦"）。
- ⛔ 不 vendor 假 shm 层、不加空壳 stub、不把 SysV 悄悄换成 `shm_open`
  （`kma shm` 常驻服务的对端约定就是 SysV key，换后端 = 改产品语义）。
- ⛔ 不缩测试分母；未实测的面（本包 `kma update`）写"未测"，不写"可用"也不写"不可用"。
- 定性归主代理：平台内核/安全策略面，不是配方缺陷，也不构成"无法适配"。

## 五、证据件（全部在 B 机，绝对路径）

- 探针：`~/tmp/uc2/z33-kma/probe.c`（4151 B）、`probe.out`（1184 B，判决原文）、
  `probe-summary.txt`（542 B）、可执行件 `probe`（27008 B）——该目录下**没有** `probe/` 子目录。
- 上游纯净树（本轮自查读码用）：`~/tmp/uc2/z33-kma/src/kma-1.4.21/`
  （`hashmapkma.c` / `sparse.c` / `kmers.c` / `db.c` / `shm.c` / `kmmap.c` / `main.c` / `kma.c`）。
- 真机读数：`~/tmp/uc2/z33-kma/run_default.log`、`run_mmap.log`、`dbA.log`、`dbB.log`、
  `out_default.*`（四件 0 字节）、`out_mmap.res`（221 B）、`index.log`、`dist.log`。
- `kma update` 的两个 rc 只由 `~/tmp/uc2/z33-kma-fix2/up2-bare.log`（154 字节，`:2` `rc=0`）、
  `up2-i.log`（482 字节，`:2` `rc=1`）承载；旧两件 `~/tmp/uc2/z33-kma-fix/up-bare.log`（41 字节）、
  `up-i.log`（338 字节）只落 stdout、全件内无 `rc=` 行 ⇒ 不构成 rc 载体。
- 本轮复测另有：`recheck-tag-1.4.21.tar.gz`、`recheck-diff-rq.txt`。
- 门禁：`~/tmp/uc2/z33-kma/r3-verify.log`、`r3-w3.log`、`r3b-finish.log`、`r3-graph.log`。

## 六、预审判决（第 6 轮整改复跑读数；B 判定已由 hit 改判 create）

本轮**无构建**（`conanfile.py` 与 `conandata.yml` 零改动 ⇒ recipe revision 仍是
`kma/1.4.21@ohpcd/stable#8e0b36e9f5ad8a6431703b5f31993dd9`），故只跑只读的文档/知识两道检查：

- `python3 scripts/ohc-run.py draft-review <本条 id> --top 3` ⇒ **rc=0**；质量预检
  `signature=✅ root_cause=✅ rec=✅`（`~/tmp/uc2/z43-kma-fix3/draft-review-r6.log:3`）；
  真实相似正式条目 TOP3 = **E051 score=0.21**（同件 :6）/ **E246 score=0.21**（:10）/
  **E338 score=0.19**（:13）；**预审建议 create**（:16，原文在 :17「疑似新知——无高相似条目，可考虑
  人工审核后纳入」）⇒ 三态阈值（>=0.55 merge-into / 0.30-0.55 review-similar / <0.30 create）下
  **无 merge-into**，与本轮主理定案（B=create，Issue 已建并回填 #3402）一致。
- `bash ci/scripts/knowledge_check.sh <仓根>` ⇒ **`KC_RESULT=pass`、`KC_ERRORS=0`**、rc=0
  （`~/tmp/uc2/z43-kma-fix3/knowledge-check-r6b.log:24-25`，全文 25 行；KC5 读数
  `index.tsv 一致 (540 = 540)` ⇒ 本草稿对未进 index，属 DRAFT 正常形态）。
  ⚠ 首跑误把包路径当 REPO_ROOT（`knowledge_check.sh kma/1.4.21`）时打印
  `knowledge/graph/ 目录不存在，跳过` + `KC_RESULT=pass: no_graph`
  （`~/tmp/uc2/z43-kma-fix3/knowledge-check-r6.log`）——**那是参数用错造成的空过**，不作判绿依据。
- `python3 scripts/ohc-run.py graph validate` ⇒ rc=0，判决行
  `~/tmp/uc2/z43-kma-fix3/graph-validate-r6.log:170`「✅ All checks passed (169 warnings)」
  ⇒ 警告数与既存基线**同为 169**（交接账所记值），本条只向 `knowledge/drafts/` 增两枚草稿、
  不改 `knowledge/graph/`，故不构成新增缺口。

⚠ `draft-review` **不扫 `knowledge/drafts/`** ⇒ 上面"无高相似条目"只覆盖**正式条目**面，
**不能当草稿面查重凭据**；草稿面查重逐份点名见第七节。

## 七、查重逐份点名（按文件名引用，不挂 E 号——`knowledge/drafts/` 里 E 编号存在复用）

1. **`knowledge/drafts/DRAFT-ohos-sysv-shmget-sigsys.md`** —— 机制本体（本平台按 syscall 号把 SysV
   IPC 拦成 SIGSYS，第 20-24 行根因段）。本条**挂靠它、不重申报机制层**。它的「可复用修复模式」只给
   两条解法：第 36-38 行**编译期** mmap 开关（`fallback_approach: compile-time-mmap-switch`）、
   第 39-45 行手工重写 `setup_shm()`/`remove_shm()` 换 POSIX shm。本包零补丁、不换后端，用上游自带
   **运行期 argv 开关** `-mmap` ⇒ **既有条目没写的另一条解法**（按 `经验文档/手册/03-路径B与C.md:83`
   即 create 触发句）。另第 47 行称被拦 syscall 的 SIGSYS 不可捕获 ⇒ 与本条第七节第 3 点互斥，已提请裁定。
2. **`knowledge/drafts/DRAFT-E577-buffer-sysv-ipc-posix.md`** —— 第 23-27 行根因（白名单式 seccomp）、
   第 31-36 行对照表把「按 errno 写的回退 | 生效 | **永不生效**（进程已死）」写成**一般性结论**、
   第 38-44 行旁证（fork、pipe、shm_open+ftruncate+mmap、匿名 mmap 全正常）；第 36 行称本族 SIGSYS
   通常不可恢复 ⇒ 同上提请裁定。**层次差**：它有结论、没有把结论变成可执行的**静态读码判据**
   （兜底的进入条件是被拦调用的返回值还是被拦调用本身），也没有平台桩宏对照（本包
   `hashmapkma.c:27-36` 的 `#ifdef _WIN32` 恒失败宏）。本条不重申报它的表与旁证。
3. **`knowledge/drafts/DRAFT-E584-bus-sysv-ipc-sigsys-catchable.md`** —— 第 51-60 行按入口分列的处置
   清单、第 62-72 行 `## 验证结果` 表、第 79 行分流桥句（把"库自带 POSIX 回退分支"路由到既有降级条目）。
   **分列形态是隐含的**：按 点名/披露/可用面/子命令/按入口 五个关键词 grep 该件 0 命中，条目没把
   「按子命令/API 面点名披露」写成规则句；其标题（第 1 行）与第 28-29 行又称该 SIGSYS **可捕获** ⇒
   与第 1、2 点的"不可捕获/不可恢复"**互相排斥**，提请条目所有者按包、按 syscall 号裁定边界；
   本包一手读数只支持「命中 shmget 后该进程以 rc=159 终止、四件输出全 0 字节」这一事实面，
   不据任何一方定性。**层次差**：本条把分列形态写成显式判据并给出同一份 bin 内三个面的分布读数。

⇒ **组合型知识不判重**（`经验文档/手册/03-路径B与C.md:89`：查重以**完整知识条目**为单位，A+B 组合成
新解题路径的适用面本身即新增价值；被 `draft-review` 标相似时在草稿与 Issue 写明组分清单与新增路径）：
**组分清单** = 上述三件已写的机制本体 / errno 回退一般结论 / 按入口分列台账；**组合后新增的解题路径与
适用面** = ①无条件 SysV 前置探测使 else 文件回退不可达这一探测型结构判据（含平台桩宏对照）＋
②同一道墙按子命令分面的分布读数与披露判据 ＋ ③上游自带运行期 argv 开关这条既有条目没写的解法
及其代价（零补丁、不换后端、不改 `kma shm`/`kma db` 的 SysV key 产品语义）。按 `手册/03:82` 的
条目外新行为偏差条件同样成立（见第三节），故 B 判定为 **create**，Issue #3402 已建并回填号。