# DRAFT: HarmonyOS PC 上 /proc 单文件按 syscall 粒度受限 —— `open()+read()` 可、`stat()/lstat()/fstat()` 返 EACCES，"先 stat 再读"的工具在确实可读的文件上报 `Permission denied`

- **草稿 ID**: DRAFT-ttyload-0.5-20131024-gitf949537-harmonyos-proc-stat-denied-read-allowed
- **来源库**: ttyload 0.5-20131024-gitf949537（归档 `archives/t/ttyload/0.5-20131024-gitf949537/`；上游 `Version` 文件实物 = 0.5.3）
- **实测环境**: HarmonyOS PC（B 机，aarch64，HongMeng Kernel 1.12.0 `#1 SMP Wed Apr 29 10:16:03 UTC 2026`，Toybox 用户态），OHOS Clang 15.0.4（SDK 26.0.0.18），HiShell + toybox `sh`
- **状态**: 草稿（待主编 promote 为正式 E 条目）

## 一句话结论

同一个进程、同一个 `/proc/loadavg`，`open(O_RDONLY)` + `read()` 成功拿到 33 字节真实负载，
而 `stat()`、`lstat()`、以及**对已经成功打开的 fd 调 `fstat()`** 全部返回 `EACCES(13)`；
`access(R_OK)` 又回答"可读"。⇒ 本平台上"**能不能读 /proc 的某个文件**"不是一个布尔事实，
而是按 *路径 × syscall 类别* 分裂的三元组；凡实现上"先 stat 再读"的工具都会把它误报成不可读。

## 现象（三层，全部真机实测）

1. **工具层（最容易被误读的一层）**：PATH 上 `/data/service/hnp/bin` 优先于 `/usr/bin`，
   裸命令名 `grep`/`awk` 拿到的是 **GNU grep 3.12 / gawk 5.4.0**（实测
   `readlink /data/service/hnp/bin/grep` = `../grep.org/grep_3.12/bin/grep`，
   `.../awk` = `../gawk.org/gawk_5.4.0/bin/awk`；而 `cat/sed/head/cut/ls/stat/test` 在 hnp 里
   **不存在**，落到 `/usr/bin/* -> ../../bin/toybox`）。于是：

   | 命令（都作用于 `/proc/loadavg`） | rc | 输出 |
   |---|---|---|
   | `/usr/bin/cat /proc/loadavg` | 0 | `21.750 21.533 21.638 4/191 33445` |
   | `/usr/bin/sed -n 1p`、`head -n 1`、`cut -f1 -d' '`、`od -c`、`wc -c`（文件参数） | 0 | 正常 |
   | `/usr/bin/grep -c . /proc/loadavg`（toybox） | 0 | `1` |
   | `/data/service/hnp/bin/busybox grep -c . /proc/loadavg` | 0 | `1` |
   | `/data/service/hnp/bin/grep -c . /proc/loadavg`（GNU 3.12） | **2** | `grep: /proc/loadavg: Permission denied` |
   | `/data/service/hnp/bin/awk 1 /proc/loadavg`（gawk 5.4.0） | **2** | `awk: fatal: cannot open file `/proc/loadavg' for reading: No error information` |
   | `/usr/bin/ls -l /proc/loadavg`、`/usr/bin/stat -c %s` | **1** | `Permission denied` |
   | `/usr/bin/test -r /proc/loadavg` | 0 | 判"可读" |

   ⇒ 只看工具矩阵会得出"**/proc 访问按工具不对称**"的结论 —— 那是**症状**，不是机制。

2. **机制层（纯 libc 探针，单进程内比较）**：32 行、零三方依赖的 C 探针
   （源码见下节，实物 `~/tmp/uc2/z75w-ttyload/probe2.c`）对每个路径依次做
   `stat/lstat/access(R_OK)/open/read/fstat` 并打印 errno。**同一进程、同一凭据**下的实测：

   | 路径 | stat | lstat | access | open | read | fstat(fd) |
   |---|---|---|---|---|---|---|
   | `/proc/loadavg` | **FAIL/13** | **FAIL/13** | ok | **ok** | **33/0** | **FAIL/13** |
   | `/proc/uptime` | **FAIL/13** | **FAIL/13** | ok | **ok** | **19/0** | **FAIL/13** |
   | `/proc/stat` | ok | ok | ok | ok | 63/0 | ok |
   | `/proc/meminfo` | ok | ok | ok | ok | 63/0 | ok |
   | `/proc/vmstat` | ok | ok | ok | ok | 63/0 | ok |
   | `/proc/cpuinfo` | ok | ok | ok | ok | 63/0 | ok |
   | `/proc/net/dev` | ok | ok | ok | ok | 63/0 | ok |
   | `/proc/self/status` | ok | ok | ok | ok | 63/0 | ok |
   | `/proc/self/stat` | ok | ok | ok | ok | 63/0 | ok |
   | `/proc/sys/kernel/hostname` | ok | ok | ok | ok | 10/0 | ok |
   | `/proc/version` | FAIL/13 | FAIL/13 | FAIL/13 | FAIL/13 | — | — |
   | `/proc/cmdline` | FAIL/13 | FAIL/13 | FAIL/13 | FAIL/13 | — | — |
   | `/proc/diskstats` | FAIL/13 | **ok** | FAIL/13 | FAIL/13 | — | — |
   | `/proc/1/status` | FAIL/13 | FAIL/13 | FAIL/13 | FAIL/13 | — | — |
   | `/etc/os-release`（对照） | FAIL/2 | FAIL/2 | FAIL/2 | FAIL/2 | — | — |

   （`FAIL/n` = 返回 -1 且 `errno=n`；13=EACCES，2=ENOENT。`read=x/0` 中 x 为读到的字节数。
   原始日志：`~/tmp/uc2/z75w-ttyload/probe-proc-syscall.log`、`probe-proc.log`。）

   关键行是 `/proc/loadavg` 与 `/proc/uptime`：**`open` 成功之后对同一个 fd 调 `fstat` 仍然
   EACCES** ⇒ 被拒的是 `getattr` 这个权限位，与"文件能不能被打开"完全无关；
   `/etc/os-release` 那一行证明探针能区分 13 与 2（不是"全部塞成 EACCES"的假象）。

3. **归因层（为什么 GNU grep/gawk 失败而 toybox/busybox 不失败）**：
   GNU grep 对每个文件参数先 `stat` 以决定读取策略（是否 mmap、是否常规文件），
   `stat` 失败即报 "Permission denied" 并跳过，**根本没调 open**；
   gawk 打印的 `No error information`（errno==0）正是"错误来自 stat 分支、errno 已被清"的指纹。
   两条**阴性对照**把"进程域/凭据"这一竞争性解释排除掉：
   - 同一份 GNU 二进制换成 stdin 形态就成功：
     `cat /proc/loadavg | grep -c .` → rc=0（`1`）；`cat /proc/loadavg | awk '{print $1}'` → rc=0（`21.750`）。
   - 同一份 GNU 二进制在 `stat` 被允许的 proc 文件上以文件参数形态也成功：
     `grep -c . /proc/stat` → rc=0（`28`）；`awk 1 /proc/stat` → rc=0（28 行；本窗 04:33 复测 awk 1 /proc/stat 的行数计数 = 28，与同行 grep -c . /proc/stat 的 28 一致，原写 27 无在盘出处）。
   ⇒ 唯一变量是"该路径允许不允许 getattr"，不是"哪个二进制/哪个 SELinux 域"。

## 最小复现（32 行，纯 libc，零三方代码）

> 行数口径：本节内嵌清单 32 行；实物 `~/tmp/uc2/z75w-ttyload/probe2.c` 同为 32 行
> （`wc -l` = 32，非空行亦 32，sha256 前缀 `6e9c0df8`），两者只差首行注释的措辞。
> 旧版 `probe.c` 是 33 行，不是本清单。

```c
/* probe2.c — 逐路径报告 stat/lstat/access/open/read/fstat 的成否与 errno */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>
#include <sys/stat.h>
static void one(const char *p)
{
    struct stat st;
    int fd, rc;
    printf("%-24s", p);
    errno = 0; rc = stat(p, &st);  printf(" stat=%s/%d", rc ? "FAIL" : "ok", rc ? errno : 0);
    errno = 0; rc = lstat(p, &st); printf(" lstat=%s/%d", rc ? "FAIL" : "ok", rc ? errno : 0);
    errno = 0; rc = access(p, 4);  printf(" access=%s/%d", rc ? "FAIL" : "ok", rc ? errno : 0);
    errno = 0; fd = open(p, O_RDONLY); printf(" open=%s/%d", fd < 0 ? "FAIL" : "ok", fd < 0 ? errno : 0);
    if (fd >= 0) {
        char b[64];
        ssize_t n;
        errno = 0; n = read(fd, b, sizeof(b) - 1); printf(" read=%ld/%d", (long)n, n < 0 ? errno : 0);
        b[n > 0 ? n : 0] = 0;
        errno = 0; rc = fstat(fd, &st); printf(" fstat=%s/%d", rc ? "FAIL" : "ok", rc ? errno : 0);
        printf(" head=[%.26s]", b);
        close(fd);
    }
    printf("\n");
}
int main(int argc, char **argv)
{
    int i;
    for (i = 1; i < argc; i++) one(argv[i]);
    return 0;
}
```

```sh
clang -O0 -w -o probe2 probe2.c && ./probe2 /proc/loadavg /proc/uptime /proc/stat /proc/diskstats /proc/1/status
# /proc/loadavg  stat=FAIL/13 lstat=FAIL/13 access=ok/0 open=ok/0 read=33/0 fstat=FAIL/13 head=[21.750 21.533 21.638 4/193]
# /proc/uptime   stat=FAIL/13 lstat=FAIL/13 access=ok/0 open=ok/0 read=19/0 fstat=FAIL/13 head=[13786.55 185148.79]
# /proc/stat     stat=ok/0 lstat=ok/0 access=ok/0 open=ok/0 read=63/0 fstat=ok/0 head=[cpu  5347522 1663 2850882 ]
# /proc/diskstats stat=FAIL/13 lstat=ok/0 access=FAIL/13 open=FAIL/13
# /proc/1/status  stat=FAIL/13 lstat=FAIL/13 access=FAIL/13 open=FAIL/13
```

## 方案

**推荐（`open-read-without-stat-gate`）**：取 `/proc` 的值只走被证明可用的 `open+read` 路径。

- **C 侧**：直接 `fopen()`/`open()+read()`，**不要用 `stat()`/`fstat()` 的成功与否门控 `open()`**；
  需要长度就按 procfs 惯例读到 EOF，把 `fstat` 的 EACCES 当"size 未知"而不是"不可读"。
  ttyload 恰好是正面样本：`arch/Linux/getload.c:1` 定义 `LOADFILE "/proc/loadavg"`、
  `:26` 直接 `fopen(LOADFILE, "r")`、`:32` `fscanf` —— 全程不 stat，所以在 HarmonyOS 上零改动可用。
- **脚本侧**：用 `sed -n 1p` / `head -n 1` / `cut` / `tr` 取值；确实要用 GNU grep/awk 就改管道形态
  `cat /proc/X | grep …`（open 由 cat 完成，GNU 工具不再对该路径 stat）。本包消费者测试的
  T3 断言即取数 `KERNEL=$(sed -n 1p /proc/loadavg | cut -f1 -d' ')`
  （`archives/t/ttyload/0.5-20131024-gitf949537/test_package/test_ttyload.sh`）。

**回退（`substitute-toybox-or-busybox-applet`）**：不便改形态时显式调用不做 stat 预检的同名
applet（`/usr/bin/grep`、`/data/service/hnp/bin/busybox grep` 实测 rc=0）。⚠ 这是绕症状：
hnp 在 PATH 里优先于 `/usr/bin`，裸命令名拿到的是 GNU 版，同一个包换台机器就可能翻。

**禁止 1**：用 `test -r` / `[ -r ]` / `stat` 的结果推断 `/proc` 文件可读性 ——
本平台 `access` 与 `open` 一致而与 `stat` 不一致（loadavg），`stat` 与 `lstat` 又能分叉
（diskstats：stat=EACCES 而 lstat=ok）。拿任一条当判据都会得出相反结论。
**禁止 2**：把 GNU 工具的 `Permission denied` 定性成"该平台读不到 /proc"从而放宽断言、
逐项 `test_skipped` 或上报"无法适配" —— 同路径 `open+read` 实测成功，断言完全可以做实。

## 适用边界与反例

- **适用**：任何读 `/proc` 下"无长度语义"文件的实现 —— loadavg/uptime/stat/vmstat/net/dev
  类监控与指标采集（`getloadavg(3)`、sysstat、htop 家族、JVM/.NET/Go 运行时指标）、
  configure/meson 里用 `grep`/`awk` 解析 `/proc` 的能力探测、以及"先 stat 再 open"的通用
  文件封装（C++ `std::filesystem`、Python `pathlib` 在 open 前的 `exists()/stat()`）。
- **反例（不在本条范围）**：`/proc/1/status`、`/proc/version`、`/proc/cmdline` 连 `open` 都被拒
  （EACCES），那是真的不可用，属"逐项降级"问题（E429/E324 的边界）；
  `/proc/diskstats` 是"整条路径不可读 + lstat 可"，与这里"可读但不可 stat"方向相反。
- **限定与解除条件**：本条结论限定到 HongMeng Kernel 1.12.0 + 该镜像的 hnp 工具集版本
  （grep 3.12 / gawk 5.4.0）。若平台放开 procfs 的 getattr，症状消失但"`open+read` 才是
  可读性判据"这条实现纪律仍然成立、不必回改。
- **风险**：把取值语句写成 `awk ... /proc/loadavg` 在 CI 里表现为"偶发读不到负载"，
  换机器/换镜像（hnp 未装 gawk 时落回 toybox）就"自己好了"，最难定位 ⇒ 落盘时优先用
  `sed|cut` 形态，并在测试脚本注释里指名本条。

## 查重差异（四条范围，命令与命中数）

| 范围 | 命令（在 worktree 根执行） | 命中 |
|---|---|---|
| 正式图谱索引 | `/usr/bin/grep -inc "loadavg" knowledge/graph/index.tsv` | 1（第 550 行 E324） |
| 正式图谱索引 | `/usr/bin/grep -inc "uname -s" knowledge/graph/index.tsv`、`-inc "ARCHLINKS"` | 0、0 |
| 正式图谱目录 | `/usr/bin/grep -ril "fstat" knowledge/graph \| wc -l` | 5 个文件：`E008.kv`、`E076.kv`、`E161.kv`、`index.tsv`、`principles.kv`（逐条读根因，均为 **fd 侧**（管道/终端/套接字）受限，无 procfs 路径侧 getattr 条目） |
| 草稿目录 | `/usr/bin/grep -ril "loadavg" knowledge/drafts/ \| wc -l` | 0（今日重跑为 2，即本条草稿自身的 .kv 与 .md 两件自我命中；写作时该目录无同类＝0） |
| 草稿目录 | `/usr/bin/grep -ril "/proc/loadavg" knowledge/drafts/ \| wc -l` | 0（今日重跑为 2，即本条草稿自身的 .kv 与 .md 两件自我命中；写作时该目录无同类＝0） |
| 草稿目录 | `/usr/bin/grep -ril "getattr" knowledge/drafts/ \| wc -l` | 20（今日重跑为 22，差值 2 即本稿 .kv/.md 两件自我命中；排除本稿后与写作时一致），逐行核对全部是 `tcgetattr`/`mq_getattr`/Python `getattr()`，无 procfs getattr（例：`DRAFT-ohos-mqueue-stub.kv:18`、`DRAFT-csstidy-1.4-zip-backslash-source-drop.md:43`） |
| 草稿目录 | `/usr/bin/grep -ril "fstat" knowledge/drafts/ \| wc -l` | 11（今日重跑 13，差 2 为本稿两件自我命中；排除本稿后不变），唯一涉及 procfs 的是 `DRAFT-10686-skypat-perf-events-runtime-capability-probe.md:160` 对 E008 的引用 |
| 框架草稿池 | `/usr/bin/grep -ril "loadavg" knowledge/draft/ \| wc -l` | 0（该目录实测只有 2 个文件 = `DRAFT-duckdb-1.5.5-build-time-target-binary-platform-probe` 的 .kv/.md 成对，`git ls-files` 同 2；无 loadavg/getattr/fstat 命中） |
| 通用池（Windows 侧，只读） | `分别用三个单字面量各跑一次 grep -ril "loadavg"、"getattr"、"/proc/" 于 经验文档/B草稿库/` | 3 个文件（`DRAFT-PKG-VER-non-ascii-build-path-breaks-locale-decoded-load-paths.kv 与其同名 .md 两件`、`README.md`），机制不同：前者是 HMDFS 路径编码，后者是用法说明；无 /proc 机制件 |

⚠ 上表所有计数一律用**单一字面量模式**：本机的 `/usr/bin/grep`（toybox）在 BRE 里写 `\|`
交替时**静默不匹配**（本窗实拍两次：查 `ttyload.c` 的 optstring、查 verify 日志的 Verdict 行，
都返回空而 rc=0），已按仓内既有记录 `经验文档/B草稿库/DRAFT-PKG-VER-toybox-grep-bre-alternation-never-matches.md`
规避；改用 GNU grep（裸命令名 `grep` = `/data/service/hnp/bin/grep` 3.12）或多条命令分别执行。

与既有条目的**层次差**（逐条指到行号）：

- **E008**（`knowledge/graph/E008.kv:19-23`）：根因写的是"对**非普通文件**（管道/终端/套接字）
  的 `fstat()/lseek()` 返 EACCES"。本条是**普通-looking 的 procfs 文件**（`/proc/loadavg`、
  `/proc/uptime`）连 `stat()`/`lstat()` 也被拒，且**明确给出"同一 fd 的 fstat 也 EACCES、而
  open+read 成功"这一"权限位分裂"证据**，并给出区分二者的判据（把失败变量从"文件类型"改判为
  "该路径的 getattr 权限"）。E008 的 `verification_cmd` 是 `strace -e fstat cat /dev/null`（设备无 strace），
  本条给出无需 strace 的纯 libc 探针。
- **E076**（`knowledge/graph/E076.kv:13-17`）：与 E008 同族，主张鸿蒙内核对**管道/终端/套接字等
  非文件描述符**的 `fstat()/lseek()` 返 EACCES/EPERM；其 `verification_cmd`（`:18-25`）探针是
  `fstat(0)`（fd 0 = stdin 管道），修复模板是 `#ifdef __OHOS__` + `OHOS_FSTAT` 宏（`:30-33`）。
  本条对象**不在 fd 侧**：`/proc/loadavg` 是已经 `open()` 成功的普通 fd，对它 `fstat()` 仍
  EACCES 而 `read()` 正常（"fd 有效、内容可读、属性不可取"），按 E076 的"非普通文件"分类会被
  判成普通文件而漏掉 ⇒ 需要的是"不要用属性判定可读性"这条独立纪律，与 E076 不重叠。
- **E031**（`knowledge/graph/E031.kv:16-19`（另 `:22` rec_approach=sudo-run））：根因写成"策略限制普通用户访问 /proc，导致读取
  `/proc/stat`、`/proc/meminfo` 失败"，推荐 `sudo -E htop`。**本窗实测与该条的
  `verification_cmd`（`cat /proc/stat # Permission denied`）在 B 机 HongMeng 1.12.0 上不复现**：
  `cat /proc/stat` rc=0 并输出 28 行、`/proc/meminfo` 亦全 ok。建议主编把 E031 的受影响面
  收窄到"htop 整体受限/按 pid 目录受限"，本条只主张"单文件 getattr 被拒而 read 可用"这一层。
- **E009**（`knowledge/graph/E009.kv:19-25`，SELinux 域转换拒绝 *执行* hnp_file 里的工具）：
  轴不同（execute vs read），且本条的阴性对照（同一 GNU 二进制经 stdin 成功、在 `/proc/stat`
  上以文件参数成功）恰好**排除**了"因为 grep 来自 hnp 所以被域拒绝"这一域解释。
- **E161**（`knowledge/graph/E161.kv:13-15` 与 `:19-20`，本条**与它方向相反、必须互指**）：
  E161 讲的是 GNU coreutils 对 **stdin（fd 0）** 做 `fstat()/stat()` 被拒 ⇒ 推荐
  `avoid-pipe-use-files`（"用临时文件代替管道"）。本条是它的**镜像面**：`/proc` 下的文件
  **作为文件参数**时反而因为同一次 `stat()` 预检被拒，而管道形态是唯一可用路径。
  两件事若混在一起，按 E161 的建议"改管道为文件"就会把本条的可用形态改坏。
  ⇒ 分工判据（本窗 B 机 2026-09-27 实测）：卡点在 **stdin** 时看 E161；卡点是
  **/proc 路径 + 工具先 stat** 时看本条。
  同时留下对 E161 的**复现边界修正**证据：该机 **未安装 GNU sort/tail**
  （`/data/service/hnp/bin/sort`、`.../tail` 均 `inaccessible or not found`，只有
  grep 3.12 / gawk 5.4.0 / busybox），`echo test | /usr/bin/sort` 与
  `echo test | /usr/bin/tail -n 1` 均 rc=0，`echo test | /data/service/hnp/bin/grep -c .` 亦 rc=0
  ⇒ E161 的 `verification_cmd`（`echo "test" | sort`）在当前镜像上不复现，其"管道必挂"结论
  应限定到"确实装了 GNU coreutils 且 fd 0 为管道"的环境；本条不据此否定 E161，只登记边界。
- **E429**（`knowledge/drafts/DRAFT-11233-harmonyos-proc-diskstats-root-only-degrade.kv`，id 占位 E429）：
  `/proc/diskstats` 是"open 与 access 全 EACCES、只有 lstat 可"，即"整条路径不可读 ⇒ 优雅降级"；
  本条是"路径可读但不可 stat ⇒ 假不可读"。两者互补且**方向相反**，本条还给出"不要用
  `test -r`/`stat` 当可读性判据"的取证纪律（E429 未覆盖）。
- **E324**（`knowledge/graph/E324.kv:16-26`）：讲的是"单项指标探针失败不要把整包指标拖成 fatal"
  （聚合层的降级策略）。本条讲的是**单个文件内部的 syscall 层**，且给出"其实根本不用降级、
  换个 syscall 序列就能拿到真值"的前置判据；两者可叠用，不构成重复。

**新增价值（一句话）**：把"某工具读不到 /proc"从工具/域问题**重判**为"该路径的 getattr 权限"
问题，给出可复算的 15 路径 × 6 syscall 矩阵、两条阴性对照，以及"open+read 才是可读性判据"
这条能直接写进配方与 C 补丁的操作纪律。

## 本包内的触发链（供审阅对照）

- `Makefile:37-38` 的 `test:` 目标就是 `./ttyload -i 1`；`ttyload.c:38` 的 optstring 为
  `"i:hvmr:c:"`（无迭代上限），usage 文案 `ttyload.c:54` 自述 "(Note: use ctrl-C to quit)"
  ⇒ 裸跑永不出头，只能在 `test_package/test_ttyload.sh` 里用"stdout 交给 head、读够 40 行
  即 SIGPIPE 收尾"做有界执行。
- 该脚本的 T3 要把 ttyload 标题行里的 1 分钟负载与内核 `/proc/loadavg` 比对（在盘实测
  `ttyload=21.53 / kernel=21.383`，见归档 `reports/conan-create.log:101-102`；同件另一轮 22.18/21.916 见 `reports/w3-local-ci.log:303`）—— 取数语句若写成 `awk ... /proc/loadavg` 或
  `grep ... /proc/loadavg` 就会在 CI 上稳定失败，本条机制正是在这一步被测出来并写进取证脚本注释的。
