# LP64 上「指针经 int 中转存放」：编译链接零告警，只在表里第一条记录被解引用时 SIGSEGV

- **草稿 ID**: DRAFT-isoqlog-2.2.1-pointer-stored-through-int-lp64
- **来源**: isoqlog 2.2.1 HarmonyOS PC 适配（HTML 报表生成阶段稳定段错误 rc=139 的定位与修复）
- **分类**: lp64 / portability / memory / runtime / consumer-test
- **状态**: 本地草稿（路径 B 知识库扩展申请中）

## 问题 / 错误签名

一个 2003 年前后的 C 程序在 OHOS aarch64（LP64）上：

- **崩溃完全没有输出**：进程被 SIGSEGV 杀掉，退出码 139，stdout/stderr 停在它自己的
  启动横幅（isoqlog 停在 `logtype:sendmail / logstore:...`）之后，没有任何错误行可 grep；
- **决定性判别特征：空数据集跑通，只要有一条记录就必崩**。同一个修复前二进制、同一份配置，
  只换日志内容（逐行取证留档 `~/tmp/uc2/hw-2/isoqlog-2.2.1/bisection-htmlcount-evidence.log`）：

  | 输入日志 | 退出码 | 产出 `*.html` |
  |---|---|---|
  | 0 行（空文件） | **0** | 13（报表全套写完） |
  | 1 行 `from=<a@b>`，但**无** `size=`（在记账调用前提前 return） | **0** | 13 |
  | 1 行 `from=<a@b>, size=1024` | **139** | 1 |
  | 1 行 `to=<a@b>, size=2048` | **139** | 5 |
  | 1 行 `from=<alice>`（无 @，走 hostname 分支）带 size | **139** | 9 |
  | 1 行 `to=<bob@nodomain>, size=512` | **139** | 9 |

  这张表把故障面从"解析器"精确夹到"记账调用之后"——**崩溃与输入内容无关、与记录条数强相关**，
  这是"某条链表的表头指针被截断"的典型形状，不是解析逻辑出错。
- 编译期与链接期**零告警**（默认 `-Wall` 也不报），因为窄化是**显式写出来的**：
  `SortDomain.allusers[n] = (int)usr;`，且读回时又显式 `(user *)` 转回去。

## 根因

`isoqlog` 的排序表把「指向 `user` 结构的指针」当成「整数」存：

```c
/* Data.h —— 元素类型是 int*，装的本该是 user* */
struct SortDomain { int nval; int max; int *allusers; } SortDomain;

/* Data.c —— 写入时把指针窄化成 int */
SortDomain.allusers[SortDomain.nval] = (int)usr;

/* Html.c —— 读回时再显式转成指针并解引用 */
u = (user *)SortDomain.allusers[i];
if (u->from_cnt == 0) break;      /* <-- SIGSEGV 在这里 */
```

- LP64（aarch64 / musl）：`sizeof(int) == 4`，`sizeof(user *) == 8`；
- 设备 jemalloc 堆地址量级（真机 `cat /proc/self/maps` 两次取证，留档
  `~/tmp/uc2/hw-2/isoqlog-2.2.1/heapaddr-evidence.log`）：诊断期见
  `6376c20000 / 6377001000 / 6377401000`，2026-09-24 19:3x 复取
  `6386a01000-6386c01000 rw-p [anon:native_heap:jemalloc]` —— **恒在 `0x63_xxxxxxxx` 量级，
  远超 32 位可表示范围**（ASLR 让每次具体值不同，所以判别时看"量级"而不是背某个地址）；
- 截断后只剩低 32 位（如 `0x77001000`），再按 `int → 指针` 符号扩展成
  `0xFFFF_FFFF_7700_1000`，该地址未映射 ⇒ 解引用即 SIGSEGV；
- ILP32（32 位 x86/ARM）两型同宽，同一份代码永不触发，所以上游 20 年没人发现；
- **为什么空数据集能过**：`sortUsersFrom()` 只在 `globusers[]` 里有条目时才调用
  `addUserToSortTab()`；0 条 ⇒ `SortDomain.nval == 0` ⇒ Html.c 的 `max = 0` ⇒
  循环体一次都不执行 ⇒ 没有任何指针被解引用。崩溃需要"第一条记录"作为触发条件。

> **通用规律**：LP64 迁移里，"指针经 `int` 中转"有三种形态，**只有一种会被编译器拦住**：
> ①隐式转换，或指针与整数的有序比较（`int p = strstr(...)` 之后 `p > 0`）——clang 15 直接报错，好办
> （见 `DRAFT-gli-0.8.2.0-strstr-pointer-compare-clang15`）；
> ②显式 `(int)` 窄化后再 `(T*)` 转回（本条）——**编译链接零告警**，只在运行时崩，
> 且常见于"自管理索引表/排序表/哈希桶数组"这类把指针当 key 搬运的老数据结构；
> ③用 `long`/`ULONG` 一类 typedef 承载 on-disk 字段或分配器布局，随字长漂移——
> 见同族 `E595-unace-lp64-addsize-readheader-makefile`（ULONG 宽度 + 解析宏指针不推进导致字段整体错位）
> 与 `E638-ppmd-20050811-lp64-i386-era-cpp-port`（分配器单元按 i386 的 4+4+4 布局）。
> 判据：**症状与记录条数强相关、与内容无关** ⇒ 先查"指针住在 int 里"，而不是先查解析逻辑。

## 无调试器时的定位手法（本机 lldb 不可用）

设备上 `lldb` 直接罢工（`Error relocating .../liblldb.so: PyExc_AttributeError: symbol not found`），
`ulimit -c` core 也无从谈起，所以拿不到回溯。可用的替代路径按成本排序：

1. **按数据量二分**（本条采用，最有效）：固定配置与输入形状，只改**记录条数**和
   **是否进入可疑调用**（利用"提前 return 的分支"当探针，例如本例 `from=` 行缺 `size=` 时
   会在 `checkUser()` 之前返回）。"0 条 OK / 1 条崩 / 走早退分支 OK"三格即可把故障面
   夹到某个调用之后，不需要任何调试设施。
2. **读代码找窄化点**：锁定嫌疑函数后，`grep -n '(int)'` 与其操作的容器声明
   （`int *`/`long *` 字段名带 `allusers/items/entries/heads` 之类）——**容器元素类型
   与它实际承载的类型不一致**，一眼可辨。
3. printf 检查点：把嫌疑循环改成"先打印指针值再解引用"，用 `%p` 对比期望地址。
   本例用 1/2 已定位，未走到这步。

## 最小修复方案

**把容器元素类型改成它真正承载的类型，并让所有 `sizeof` 跟着变**（纯类型修正，零语义改动）：

```diff
 /* Data.h */
 struct SortDomain {
 	int nval;
 	int max;
-	int *allusers;
+	user **allusers;
 } SortDomain;
```

```diff
 /* Data.c :: addUserToSortTab() */
-	int *u;
+	user **u;
-	SortDomain.allusers = (int *)malloc(NVINIT * sizeof(int *));
+	SortDomain.allusers = (user **)malloc(NVINIT * sizeof(user *));
-	u = (int *)realloc(SortDomain.allusers, (NVGROW * SortDomain.max) * sizeof(int *));
+	u = (user **)realloc(SortDomain.allusers, (NVGROW * SortDomain.max) * sizeof(user *));
-	SortDomain.allusers[SortDomain.nval] = (int)usr;
+	SortDomain.allusers[SortDomain.nval] = usr;

 /* Data.c :: 8 个 sort*() 的交换变量（它们也在 int 里搬指针） */
-	int tmpnval, i, j, max, tmp;
+	int tmpnval, i, j, max;
+	user *tmp;
```

交付形态：`archives/i/isoqlog/2.2.1/patches/0001-isoqlog-Data.h.patch`（18 行）与
`0002-isoqlog-Data.c.patch`（219 行），逐文件、`a/`、`b/` 前缀、10 行上下文，在设备侧由框架自身的
差分与校验函数（`ohc.refresh_patch._diff_files` + `_validate_patch_format` + `_dry_run`，
即 `refresh-patch --auto` 内部同一套代码路径）对 pristine / 已改两份树生成；
`conandata.yml` 两条各显式 `strip: 1`（pristine 树上 `-p1` dry-run rc=0，`-p0`/`-p2` 均 rc=1）。

### 已尝试与放弃的方案（含失败原因）

| 方案 | 结果 | 为什么不用 |
|---|---|---|
| 给编译器加 `-fcommon` / 关严格别名 / 换 `-m64` 类开关 | 不解决 | 这是**源码类型错误**，不是代码生成选项问题（`-fcommon` 解决的是同包另一个 `duplicate symbol` 问题，两回事） |
| 元素类型改 `long *`、写入 `(long)usr` | 能过 LP64 | ①在 LLP64（Windows）上 `long` 仍是 32 位，假设照样失效；②8 个排序函数的交换变量仍须同步改类型，改动量与正解相同，却把错误假设留着。**要嘛用真实指针类型，要嘛用 `intptr_t`**，不要用 `long` |
| 只把 `(int)usr` 改成 `(intptr_t)usr` 而不动字段类型 | 仍崩 | 字段是 `int *`，写入 `intptr_t` 又会被截回 32 位；而且交换变量 `int tmp` 会在排序过程中二次窄化——**窄化点必须逐个消灭，改一处不够** |
| 升级到上游更新版本 | 不可得 | 上游自带 `ChangeLog` 的最新条目就是 `Version 2.2.1 Feb 23, 2005`（`configure.in:AC_INIT(isoqlog, 2.2.1, bug-report@enderunix.org)`），19 年无后继发布；上游站 `www.enderunix.org` 本机 `curl` 无任何 HTTP 响应（根路径与下载路径皆然），SourceForge 上亦无该文件（`projects/isoqlog/files/isoqlog-2.2.1.tar.gz` 及 `master.`/`ayera.`/`downloads.` 三个镜像前缀实测 404）⇒ **只能靠本地补丁修正，不能靠升版绕过** |

## 实际验证结果

- **修复前**（真机 `conan create`，create-07 前的 06 轮）：打包件 `-h/-v/配置校验` 全过，
  一旦喂进 1 条可解析邮件行即 `rc=139`。当时那轮 10 条断言**全部执行完毕**
  （`create-06.log:576` = `ISOQLOG_TEST_ASSERTIONS pass=4 fail=6`）：断言 1–4 是 CLI 冒烟全绿，
  断言 5（真实日志分析）拿到 `rc=139` 而失败，其后 5 条报表内容断言因 HTML 报表在途中断而
  **连带失败**——不是"没执行"。脚本故意不用 `set -e`，正是为了在崩溃后仍打印这条完整计数。
  （同一轮日志还有一行 `[skip] date arithmetic unsupported on this shell`，属当时那版脚本的
  日期算术探测分支，不计入 pass/fail；现行 12 断言版已无该分支。）
- **修复后**（create-10.log，487 行全绿，sha256 前缀 `7e40687c`，recipe rev `34c2c8fdb3592d1b62a9feabd7d46411`）：`conan create` G0-G4 通过，
  `test_package` 消费者测试 **12/12** 断言通过，其中「真实日志分析退出 0」「13 份 HTML 报表」
  「发件人 1024 字节单条值」「512+1024 求和后渲染为 `1.50 KBytes`」「非当月行被日期闸门忽略」
  五组都依赖此前崩溃的那段代码。与上面那条 `fail=6` 的对应关系：当时那版脚本只有 10 条断言，
  6 条失败全部集中在"日志分析及其报表输出"这一段（首条即 `rc=139`，其余为 `index.html` 缺失、
  报表份数不符、sender/receiver 未出现、报表里找不到字节合计）；现行 12 条中的
  「`1.50 KBytes` 聚合渲染」与「非当月行被日期闸门忽略」两条是修复时新增，**当时并不存在这两条**，
  其余 10 条与当时一一对应（当时最后一条的期望值是报表出现字节合计 7168，现改写为 sender
  尺寸表中出现 1024 的单条值）。`CREATE_RC=0`。

## 适用范围 / 反例 / 解除条件 / 风险

**适用**：从 ILP32 时代迁到 LP64 的 C/C++ 代码，其**自建数据结构**（排序表、哈希桶、
索引数组、"句柄表"）把指针塞进 `int`/`short`/位域，或用 `int` 存文件描述符以外的指针值。
高发特征：变量/字段名形如 `allusers/items/entries/heads/priv/data`，而元素类型是 `int *`；
或同一函数里既出现 `sizeof(int *)` 又出现 `(int)ptr`。

**不适用 / 反例**：
- **合法**的 `int → 指针` 窄化：`qsort` 的上下文参数、`pthread` 的 `void *` 里塞小整数、
  `select()`/`epoll` 的 `.fd` 字段、`atexit` 句柄、Gtk 的 `gpointer` 数据 —— 这些承载的
  本来就不是地址，不要顺手改；
- `int fd = open(...)` 之类"用 int 存整数句柄"不是本条问题（fd 本来就只有 32 位）；
- 已由编译器报出的形态（隐式转换、指针与整数的有序比较，如 `int p = strstr(...)` 后 `p > 0`）
  走 `DRAFT-gli-0.8.2.0-strstr-pointer-compare-clang15`，不必引用本条；
- 32 位目标（armv7 ILP32）上本缺陷不存在，补丁在 ILP32 上同样正确（类型变宽不会有害），
  但不必为它单独申报。

**解除条件**：上游若发布把该容器改为真实指针类型（或改用 `void **`/索引）的版本，
补丁应随之删除并回归普通打包。

**风险**：元素类型改变会影响同名字段的**所有**读写点，必须逐个核对（本例 **13** 处 =
1 处字段声明 + `addUserToSortTab` 内 4 处 + 8 个排序函数各 1 处交换变量，共落在 9 个 hunk 里）；
漏改交换变量时
症状一模一样（`int tmp` 在 swap 过程中二次截断），**改完必须用真实数据集（≥1 条记录）
验证**，空数据集验证会给出假绿。

> 同型但**确认为死代码**的兄弟容器：`Data.h` 里另有 `struct UsersTab { … int *allusers; }`，
> 元素类型与修复前的 `SortDomain` 完全同型，但全树对它的读写只在
> `Data.c::printAllUsers()` 内部一段整块 `/* … */` 注释里（无 `malloc`、无写入点、不生成代码），
> 故补丁不动它，保持"只改真实故障点"的最小 diff。按 `allusers` grep 复核时会同时命中它，
> "逐个核对"必须给出这一条结论。

## 查重与新增价值

四范围查重（2026-09-24 在 worktree `~/qzy/hw-2-isoqlog-2.2.1` 实测计数：
`ls knowledge/graph/E*.kv` = **540** 条、`ls knowledge/drafts` = **3134** 个文件，
`经验文档/适配经验汇总.md`、同类包）：

- **同族但不同签名**：`DRAFT-gli-0.8.2.0-strstr-pointer-compare-clang15`（`int p = strstr(...)`
  之后与 0 做有序比较）与 `E553-draft-70DD`（bwbasic 1990s 老代码基线：随机文件 CLOSE 后 reopen
  写 NULL 缓冲区段错误）
  —— 前者是**编译期可见**的指针/整数比较错误，clang 15 直接拒绝，修法也是逐处改类型；
  后者是 CLOSE 后 reopen 的 NULL 缓冲区段错误（分配条件按指针判空），与本条的"容器元素类型
  承载错了类型"是两种根因；
  `DRAFT-libuninum-2.7-lp64-ilp32-type-assumption-defects` 是 `wchar_t`/`unsigned long`
  **宽度混用**导致 CLI 每行单字符（症状是截断输出，不是 SIGSEGV，根因在形参类型）；
  `E595-unace-lp64-addsize-readheader-makefile`（`ULONG` typedef 变宽 + 解析宏指针不推进
  导致 on-disk 字段整体错位）、`E638-ppmd-20050811-lp64-i386-era-cpp-port`（分配器单元
  按 i386 的 4+4+4 布局、区间编码器依赖 32 位回绕）是 **LP64 结构布局/字长假设**一族
  —— 它们的症状都是"字段错乱或输出失真"，不是"指针被截断后解引用"；
  `DRAFT-hfsm2-beta73-aarch64-char-narrowing` 是 aarch64 上 `char` 窄化/符号性一族，
  症状是**值被改写**而非地址非法，且它由编译器告警可见，与本条"零告警 + 只在运行时崩"不同侧。
- **本条新增**：①"显式 `(int)` 中转 + 显式转回"这一形态**编译链接零告警**，知识库现有条目
  都停在"编译器会拦"这一侧；②给出可直接复用的**判别特征**——崩溃与记录条数强相关、
  与内容无关、0 条记录必跑通；③给出**无调试器（本机 lldb 不可用）时的定位算法**
  （按数据量二分 + 借提前 return 的分支当探针）；④给出反例清单（`long` 不够、只改写入点不够）
  与"空数据集验证会假绿"的复核要求。这四点是可跨库复用的解题路径，组分虽与既有 LP64/编译期
  形态条目有交集，
  组合后新增了一条完全不同的排查路径，按 AGENTS §6.2「组合型知识不判重」按 create 申报。
- **工具查重复核（`draft-review`，2026-09-24 于 worktree 实测）**：质量预检
  `error_signature` / `root_cause` / `recommendation` 三项全 ✅；相似度 TOP3 为
  `E338 score=0.21`（sig 0.33 / kw 0.0 / cat 0.14）、`E040 score=0.19`、`E420 score=0.00`，
  均远低于合并阈值且无一为"指针经 `int` 中转后解引用"同签名 ⇒ 预审建议 **create**，
  与上面四范围人工查重结论一致（命令形式：`python3 scripts/ohc-run.py draft-review`
  `<DRAFT stem，不带 .kv 后缀>`）。

## 触发实例（本包）

- 首错：`analysis run failed rc=139 out=`（isoqlog 消费者测试断言 5），
  此前 4 条 CLI 冒烟断言全绿 ⇒ 与"编译/链接/打包是否成功"解耦；
- 定位耗时：约 25 分钟（lldb 不可用 → 二分 8 组输入 → 读 `Data.h` 容器声明即锁定）；
- 修复后：消费者测试从修复前的 10 条断言扩为 12 条并全绿。修复前那一轮 10 条**全部执行**
  （`create-06.log:576` 逐字为 `ISOQLOG_TEST_ASSERTIONS pass=4 fail=6`），逐条构成与
  "`set -e` 为何故意不用"见上面「实际验证结果」段，此处不重复计数以免两处口径漂移。
