# kma

KMA (K-mer Mapping and Alignment) 把原始测序 reads 直接比对到冗余
DNA/蛋白数据库上：两级 k-mer 映射 + 一级比对，非唯一匹配用 ConClave
排序方案消歧并输出共识序列。上游：
https://bitbucket.org/genomicepidemiology/kma
（Clausen, Aarestrup & Lund, "Rapid and precise alignment of raw reads
against redundant databases with KMA", BMC Bioinformatics 2018;19:307）

## Version

- 1.4.21

## Build notes

Conan 配方直接驱动上游裸 Makefile（无 configure、无 install 目标，64 个 .c
一次编译通过），依赖 `zlib/1.3.1.1`（Makefile 链接 `-lz`，filebuff.c 用
`inflateInit2`），打包 `kma`、`kma_index`、`kma_shm`、`kma_update` 四个可执行
文件到 `bin/`。上游一行代码都没改。

## HarmonyOS PC 使用方式（重要）

本平台用 seccomp-BPF 按 syscall 号把 SysV IPC（`shmget`/`shmat`/`shmdt`/
`msgget`/`msgsnd`/`msgrcv`/`semget`/`semop`）击杀为 SIGSYS(31)。KMA 默认的模板
库加载路径 `hashMapKMA_load()`（hashmapkma.c:275）在
hashmapkma.c:319/349/385/416 无条件 `ftok()+shmget()` 探测共享内存，
"探测失败即回退普通文件读"（hashmapkma.c:321-330）因此不可达。

**交付用法 = 上游自带的 `-mmap` 开关**（不是补丁、不是改动上游）：它让 KMA 走
`hashMapKMAmmap()`（kmmap.c:33）的纯文件后端 mmap 路径，本平台放行。

```bash
kma index -i templates.fa -o templates
kma -i reads.fa -t_db templates -mmap -o out/name
```

以下按三种状态逐子命令登记，口径固定：**可用** = 有 rc 与产物读数；**不可用** = 有 rc 与错误原文；**未测** = 无功能读数（不得当成可用）。

在本平台**不可用**的子命令：

| 子命令 | 状态 | 依据 |
|---|---|---|
| `kma -i ... -t_db ...`（不加 `-mmap` 的默认比对） | 不可用，rc=159（128+31=SIGSYS），四个输出文件全 0 字节（一手读数 `~/tmp/uc2/z33-kma/runA.log:8` = `Signal 31 (core dumped)`，`out_default.{res,aln,fsa,frag.gz}` 实测 0 字节；数值 rc 记于设备侧 `~/tmp/uc2/z33-kma/STATE.md:69`）| hashmapkma.c:319/349/385/416；kmers.c:89、sparse.c:384 调用 `hashMapKMA_load` 的默认分支 |
| `kma db -t_db ...` | 不可用，rc=159，程序自打 `Signal 31 (core dumped)`（一手读数 `~/tmp/uc2/z33-kma/dbB.log:2`；数值 rc 记于 `STATE.md:71`）| db.c:59 直连 `hashMapKMA_load`，**没有** `-mmap` 分支（子命令级能力墙） |
| `kma shm` / `-shm 1..4` | 不可用（**本子命令未实跑**：SysV 共享内存装/卸工具定义上依赖被击杀的 syscall，依据是 syscall 探针 `~/tmp/uc2/z33-kma/probe-summary.txt:5` 与源码事实）| shm.c（唯一 `IPC_CREAT` 建立方）、main.c:57-58 |

可用面（有 rc=0 与产物读数）只有 `kma -v`、`kma index`、`kma -mmap` 比对三项；`kma dist`、`kma trim`、`kma seq2fasta`、`kma -h`、`kma update` 一律按未测登记（无功能读数，不得当成可用）；`kma map` 默认路径、`kma db`、`kma shm` 为不可用。

逐子命令一手读数（路径:行号，均为设备上现存日志；本轮未重跑构建，只对 `kma update` 用已交付产物补跑两式并记 rc，见该格。行锚按当前 `1.4.21/reports/w3-local-ci.log` 全文 384 行逐条复算，每条锚前写全被引件名）：

| 子命令 | 状态 | 一手读数 |
|---|---|---|
| `kma -v` | 可用 | `1.4.21/reports/w3-local-ci.log:302` `[run] rc=0`、`1.4.21/reports/w3-local-ci.log:303` A1 输出 `KMA-1.4.21` |
| `kma index` | 可用 | `1.4.21/reports/w3-local-ci.log:319` `[run] rc=0 (lines=19)`、`:320` A2、`:321` `testdb.comp.b` size=4208420、`:322` `testdb.length.b` size=20；另见早期轮 `~/tmp/uc2/z33-kma/index2.log:1-19`（该件只落 stdout，其 rc 读数记于 `~/tmp/uc2/z33-kma/STATE.md:69`）|
| `kma -mmap` 比对 | 可用 | `1.4.21/reports/w3-local-ci.log:339` `[run] rc=0 (lines=23)`、`:340` A5、`:342` A6（`.res` 数据行恰好 1 行）、`:344`–`:348` A7–A11（`.res` 给 `t1` / Score 300 / Query_Identity 100.00）、`:349` A12（`.aln` 头 `# t1`）、`:350` `out_mmap.fsa` 309 字节、`:351` `[result] PASS 12/12` |
| `kma dist` | **未测** | 现存两次实跑都不构成读数：`~/tmp/uc2/z33-kma/steps.log:43` `dist_rc=1` 配 `dist.log:1` `Invalid value parsed at "-d".`（首轮把选项写错，`STATE.md:67` 已自记此事）；`distB.log` 0 字节、无 rc 亦无输出，其 rc=0 只出现在 `STATE.md:35`、`:71` 的自述里 |
| `kma trim` | **未测** | 全目录无实跑留痕：`trim` 在现存日志里只出现在编译行 `1.4.21/reports/w3-local-ci.log:234`（`clang … -c -o trim.o trim.c`）与归档行 `1.4.21/reports/w3-local-ci.log:247`（`llvm-ar -csr libkma.a … trim.o …`）|
| `kma seq2fasta` | **未测** | `steps.log:42` `seq2fasta_rc=1`；`s2f.log:1-5` 与 `s2fB.log:1-5` 全文只有 usage 页（写着 `-t_db` REQUIRED），未试过有效用法 |
| `kma -h` | **未测** | 无 `kma -h` 单独实跑留痕；`1.4.21/reports/w3-local-ci.log:365` 只有 `kma --version/--help failed (non-blocking)`，那是 W3 L2 冒烟的双横线形态，不能当 `-h` 的读数（同段判决 `L2_RESULT=skip` 在 `1.4.21/reports/w3-local-ci.log:372`）|
| `kma update` | **未测** | 旧两件 `~/tmp/uc2/z33-kma-fix/up-bare.log`（41 字节）、`up-i.log`（338 字节）**只落 stdout、全件内无 `rc=` 行** ⇒ 那两个 rc 当时缺一手载体；本轮 08:44 用已交付件（`reports/w3-local-ci.log:297`、`:298` 所记的 571904 字节 bin）补跑两式并把命令行/rc/stdout 分段落盘：`~/tmp/uc2/z33-kma-fix2/up2-bare.log:2` `rc=0` + `:4` `Insuffient amount of arguments handed!!!`（上游原文如此），`~/tmp/uc2/z33-kma-fix2/up2-i.log:2` `rc=1` + `:4` `Invalid option:` 后跟制表符与 `-i`、`:6` 起为帮助页 ⇒ 未试出正确用法、无功能读数（`rc=0` 只走到 usage 打印，同样不是可用证据）|

⇒ 上述四项（`dist`/`trim`/`seq2fasta`/`-h`）此前被写进可用面，依据是已撤下草稿的自我陈述，
不构成证据；本轮按现存日志逐字复取后一律降为未测。要升为可用需另跑一次带 rc 的实跑并留日志。

## Files

- `1.4.21/` — Conan 配方、消费者测试与适配笔记（能力墙证据见
  `1.4.21/notes.md`）
