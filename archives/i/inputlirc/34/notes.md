# inputlirc 34 适配记录（HarmonyOS PC aarch64）

- 任务：平台任务号 7490，档位【中】，语言 c
- 设备：B 机，HongMeng Kernel 1.12.0，aarch64，clang 15（OHOS SDK 26.0.0.18 sysroot）
- 结论：**编译/安装/配方门禁可全绿；核心功能面被三条平台约束挡住，其中两条不是本包能绕开的**

## 0. 源码事实（逐条复算，含对预扫假设的否证）

| 预扫假设 | 复算命令 | 结果 |
|---|---|---|
| 源码 URL 与体积 | `curl -L -o inputlirc_34.orig.tar.gz <url>` + `sha256sum` | **证实**。HTTP 200、6729 字节、`6ff52376c226c7cb49fbe053365eb4931c97a9edfa503ee4ebb689598547270c` |
| 语言 c、6 文件、单 Makefile | `tar tzvf` | **证实**。`.gitignore` `Makefile` `gennames` `inputlirc.service` `inputlircd.8` `inputlircd.c` 共 6 个，`.c` 只有 1 个 |
| `Makefile` 把 `/usr/local` 与 `PREFIX` **烧死** | `grep -nE 'PREFIX\|DESTDIR\|SBINDIR' Makefile` | **推翻**。`PREFIX ?= /usr/local`、`SBINDIR/SHAREDIR/MANDIR/SYSTEMDDIR ?= …`、`INSTALL ?= install` **全是 `?=`**，命令行/环境可覆盖，不需要改源码。真正的烧死点是**内核 UAPI 头的绝对路径**（见 §1 症状一） |
| 零外部依赖 | `grep -nE 'LDLIBS\|LDFLAGS\|-l' Makefile` + 读全部 `#include` | **证实**。链接行只有 `$(CC) $(CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ $<`，无 `-l*`；include 全为 libc/POSIX + `<linux/input.h>`。`gennames` 是 `#!/bin/sh`，**不需要 perl** ⇒ 无 `-lutil/-levent/-lubacc`，不触发停手条款 |
| ★输出走 Unix 域套接字 + setuid 访问 `/dev/input` | 见 §3 逐号探针 | **前半证实、后半需分两层**：套接字确实是 Unix 域且是硬墙；**setuid 不是墙**（本包只用 `setgid()`+`setuid()`，两者在内核放行），墙在 evdev 的 DAC 权限上 |

## 1. 症状一：源码根本编译不过——绝对 `/usr/include`

**症状**
```
make: *** No rule to make target '/usr/include/linux/input-event-codes.h', needed by 'names.h'.  Stop.
```
以及 `inputlircd.c:43:10: fatal error: '/usr/include/linux/input.h' file not found`。

**根因**
上游三处把内核 UAPI 头写成绝对路径：
1. `names.h: /usr/include/linux/input-event-codes.h gennames`（前置条件，make 要求该文件存在且要有规则）
2. `./gennames $< > $@`（把同一个绝对路径当参数喂给生成器）
3. `inputlircd.c` 里 `#include </usr/include/linux/input.h>`（尖括号包绝对路径，预处理阶段硬解析）

HarmonyOS 上 **`/usr/include` 整个不存在**（`ls -d /usr/include` → No such file or directory）。
UAPI 头其实在 SDK sysroot 里，且路径含 SDK 版本号：
`/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/linux/`。
clang 的默认搜索路径**已经**含它，所以**相对尖括号包含是通的**。

**最小复现**
```sh
printf '#include <linux/input.h>\n#include <linux/input-event-codes.h>\nint main(void){struct input_event e;(void)e;return EV_KEY;}\n' > htest.c
clang -c htest.c -o htest.o     # RC=0  ⇒ 头存在，只是位置不在 /usr/include
clang -M htest.c                # 打印出 sysroot 内的真实绝对路径
```

**已试过的失败方案**
- ~~`export CC=clang` 后直接 `make`~~：绝对路径与 `CC` 无关，仍然断在 `names.h` 前置条件。
- ~~在配方里 `os.symlink` 造一个 `/usr/include`~~：需要 root，且污染全局，违反 R49「禁止注入共享系统前缀」。
- ~~把 SDK 路径写死进 `conanfile.py`~~：路径带 `ohos-sdk_26.0.0.18` 版本号，换 SDK/换 CI 机即失效，且属于 R33 禁止的"依赖环境特定值"。
- ~~给 `gennames` 传预处理输出~~：`-E` 会把 `#define` 全部消掉，生成器拿不到 `KEY_*` 表。

**最终方案**（补丁 0001）
- `Makefile` 引入 `KERNELINC ?= /usr/include`，两处绝对路径改成 `$(KERNELINC)/linux/…`；
- `inputlircd.c` 的 `#include </usr/include/linux/input.h>` → `#include <linux/input.h>`；
- 配方 `build()` 问编译器要真实目录：`subprocess.run([cc, "-M", stub])`，从依赖行里挑出
  `…/linux/input-event-codes.h` 再截掉后缀，作为 `make KERNELINC=…` 传入。
  `cc` 取自 `self.conf_info["tools.build:compiler_executables"]["c"]`（R33），不读裸 shell 变量。
  这样在装有 coreutils/内核头的 Linux CI 上会自然解析回 `/usr/include`，无需分支。

**适用边界**
适用于任何"手写 Makefile + 绝对 `/usr/include` 引用内核 UAPI 头"的上游。
若上游还要求 `names.h` 里含本 sysroot 未导出的码表，本法不覆盖（本包覆盖到了）。

## 2. 症状二：`make install` 起不来——镜像无 `install(1)`

**症状**：`install: command not found`（`command -v install` 无输出）。
**根因**：HarmonyOS 镜像不带 coreutils `install(1)`；toybox `cp` 也不认 `-m`
（`cp -m 644 a b` → `cp: Unknown option 'm'`），而 `Makefile` 有两条 `$(INSTALL) -m 644 …`。
**最小复现**：`command -v install; echo hi>x; cp -m 644 x y; echo $?`。
**失败方案**：`make INSTALL=cp` ⇒ 带 `-m 644` 的两条规则立刻挂。
**最终方案**：`INSTALL ?= install` 是 `?=`，配方在 `package()` 里生成 POSIX
`install-sh`（自己解析 `-m MODE`、`cp` + `chmod`）并从 `INSTALL=` 注入；
上游 install 规则一行不改，在有 coreutils 的机器上行为不变。
**边界**：只覆盖 `install` 与 `install -m MODE SRC DEST[-dir]` 两种调用形，
不支持 `-d/-C/-t`；本包只用这两种。

## 3. ★功能面三条墙：逐号 errno 实测表

探针：`~/tmp/uc2/z32-inputlirc/probe34.c`、`probe_w3.c`（`open()` 系，**不是** `stat()`；
特权类走 `fork()` 隔离，按 `WIFSIGNALED`/`WTERMSIG` 区分 seccomp 击杀与 errno 失败；
自我目标调用返回 0 即证明该 syscall 未被拦截，与是否特权无关）。

### 3.1 墙一 · evdev 输入面

| 探针 | 结果 | errno |
|---|---|---|
| `open("/dev/null")` | **OK** fd=3 | —（**阳性对照**） |
| `open("/dev/input")` | FAIL | **EACCES(13)** |
| `open("/dev/input/event0")` | FAIL | **EACCES(13)** |
| `open("/dev/input/mice")` | FAIL | **EACCES(13)** |
| `glob("/dev/input/event*")` | **GLOB_NOMATCH(3)**, matched=0 | — |
| `EVIOCGVERSION` / `EVIOCGBIT` / `EVIOCGNAME` / `EVIOCGRAB` | **未执行**（无可用 event fd） | — |

**归因：②权限面（经 `/dev/input` 的 open()/glob() 通路在本 uid 下不具判别性）**。三条 `EACCES` 只说明**路径搜索在父目录就被 DAC 拒**，
**不能**证明 `/dev/input` 下的节点存在：审计者自建 `audprobe.c` 复算（`reused-from-w4r1`，`~/tmp/uc2/z32-inputlirc-w4/probe0.txt:39-46`）`open("/dev/input/event0")` 与 `open("/dev/input/event-aaa-no-such-node")` **同为 EACCES(13)**，
而 `open("/dev/input-aaa-no-such-dir/event0")` 才返回 `ENOENT(2)`；`ls -ld /dev/input` 亦 Permission denied。
⇒ 本 uid 下**无法据 open() 判断节点存在与否**。`GLOB_NOMATCH` 是"列不出目录"的另一回事，**二者不得混写**。
⇒ **换通路则可判定，节点确实存在**：r2 审计者探针（`~/tmp/uc2/z32-inputlirc-w4r2/report2.txt:6-23`，源码 `r2probe/p2.c`）实测 `access("/sys/class/input/event0", F_OK)` = 0 而 `event9137` = `ENOENT(2)`，且 `/proc/bus/input/devices` 可读并列出 `event0…event16` ⇒ 被拒的是 open()/glob() 两条通路，而非"内核没有输入设备"（这条竞争解释被排除，DAC 归因因此是排他结论）。
⇒ **不得**据此声称"OHOS 没有输入设备/不支持 evdev"；也**不得**因为
`glob` 空就把 evdev 判成"内核未实现"。evdev 的 `ioctl` 面在本环境**未获证据**，
申报口径为**未执行 + 证据**，分母不缩。
本包 `open_evdev()` 失败只 `syslog` 后跳过设备（进程继续），`add_named()`
（`-n`）打印 `No event devices found!` 后返回——两条都与探针一致。

### 3.2 墙二 · setuid/降权族（**预扫假设在此被推翻**）

| syscall（自我目标，rc=0 即放行） | 结果 |
|---|---|
| `setuid(getuid())` | **OK (rc=0)** |
| `seteuid(geteuid())` | **OK** |
| `setgid(getgid())` | **OK** |
| `setegid(getegid())` | **OK** |
| `setresuid(u,u,u)` | **OK** |
| `setresgid(g,g,g)` | **OK** |
| `mlock(4096)` | **OK** |
| `daemon(0,0)` | **OK** |
| `setreuid(u,u)` | **被 SIGSYS(31) 杀**（`Bad system call`） |
| `setregid(g,g)` | **被 SIGSYS(31) 杀** |

**归因：不构成阻塞**。inputlirc 的降权只有
`if(setgid(pwd->pw_gid) \|\| setuid(pwd->pw_uid))`（`inputlircd.c:524`），
两个都落在**放行**的一边；本批 rephrase 踩的 `setreuid/setregid` SIGSYS
（E051 家族）**本包根本不碰**。
⇒ 按 E051 家族做"整族一刀切"会误判；必须**逐 syscall** 探。
预扫假设"以 setuid 方式访问 `/dev/input` 是最可能的硬墙"**推翻**：
真正的墙是 evdev 的 DAC（§3.1），不是 `setuid(2)` 的系统调用面。

顺带：默认降权目标 `-u nobody` 在本机 `getpwnam("nobody")` → **NULL（errno=0）**，
即 passwd 里没有 `nobody`。上游**有判空**（`if(!pwd){…return EX_OSERR;}`），
所以是干净退出 71 而不是段错误——预扫"未判空解引用"的担心**推翻**。
**归因：③配方可绕过**，`-u <本机存在的用户>` 即可；README 已写。

### 3.3 墙三 · Unix 域套接字落点（本包真正的硬墙）

| 落点 | 建普通文件 | `mkfifo` | `bind()` 文件系统端点 | `bind()` 抽象命名空间 |
|---|---|---|---|---|
| `$HOME` = `/storage/Users/currentUser`（**hmdfs** 挂载） | **OK** | **EPERM(1)** | **EPERM(1)** | **OK** |
| `~/tmp/uc2/z32-inputlirc`（**hmdfs**，与上一行同一文件系统） | **OK** | **EPERM(1)** | **EPERM(1)** | **OK** |
| `/dev/shm`（可写） | **OK** | EACCES(13) | EACCES(13) | **OK** |
| `/data/local/tmp`（hmfs） | EACCES(13) | EACCES(13) | EACCES(13) | **OK** |
| `/run/lirc/lircd`（**上游默认 `-d` 值**） | — | — | **ENOENT(2)**（`mkdir` 先失败：`Unable to create /run/lirc`） | — |
| `/var/run/lirc/lircd` | — | — | ENOENT(2) | — |
| `/tmp/…` | — | — | **EROFS(30)**（`/tmp` 只读，设备已知特性，非套接字问题） | — |
| `/dev/socket/…` | — | — | ENOENT(2) | — |

**归因：②平台策略面（MAC/LSM），不是①内核未实现**。

`bind(2)`/`unix(7)` 对 AF_UNIX 文件端点列出的 `EPERM` 只有一种来源
（"对该 socket 文件所在目录没有写权限"），其余候选 errno 各有明确触发条件；
下表逐个把它**排除**，因此这个 EPERM 不能拿"标准语义"一句带过：

| `bind()` 可能返回 | 触发条件 | 本机排除依据 |
|---|---|---|
| `EACCES` | 路径分量搜索权限不足 | 同目录普通文件 `open(O_CREAT)` **OK** |
| `EPERM` | **目录写权限被拒**（man 面唯一来源） | 同上；且 `$HOME` 与 `~/tmp/uc2` 两处均如此——但两者**同为 hmdfs**，故只支持"hmdfs 上成立"的结论，不构成跨文件系统证据 |
| `EEXIST` | 同名文件已存在 | `bind` 前先 `unlink()`，且探针自建唯一名 |
| `EINVAL` | 非 `AF_UNIX` 族、或 `sun_path` 首字节为 NUL 字节（抽象命名空间判据；C 源码里写作反斜杠+零两个字符，本行刻意不用真字节）而 `addrlen<=sizeof(sa_family_t)` | `sun_family=AF_UNIX`；文件系统用例首字节非 0；`addrlen=offsetof(sun_path)+len+1` |
| `ENAMETOOLONG` | `sun_path` 越界 | 最长路径 <40B，且已显式校验 `sizeof sa.sun_path-1` |
| `ENOENT` | 父目录不存在 | 父目录已实测可 `stat`/可写 |
| `EROFS` | 只读 FS | 仅 `/tmp` 返回它，其余落点返回 EPERM/EACCES |

判据是同目录的**三态对照**：普通文件可建（写权限有）+ `mkfifo` 与 `bind` **同为 EPERM**
（非常规 inode 一律拒）+ **抽象命名空间 `bind()` 成功**（AF_UNIX 子系统本身完全可用）。
⇒ 拒的是"在文件系统上创建 socket/fifo 节点"这一动作，**不是** Unix 套接字能力。
文件系统名按 `/proc/mounts` 实测（`reused-from-w4r1`，`probe0.txt:44-49`）：`/storage/Users` 是 tmpfs，
`$HOME=/storage/Users/currentUser` 与其下的 `~/tmp/uc2` 是 **hmdfs**，`/dev/shm` 是 tmpfs，`/tmp` 是 erofs(ro)。
⇒ 原先"​`$HOME` 落在 tmpfs 上仍然 EPERM，也排除了某个 FS 不支持的解释"一句**不成立、已删除**：
两个 EPERM 臂同属一类文件系统（hmdfs），而真 tmpfs 的 `/dev/shm` 返回的是 `EACCES` 而非 `EPERM`。
本节结论因此**限定为"在 hmdfs 上 bind 文件系统端点返回 EPERM"**；
总归因"拒创建非常规 inode"仍被同目录四臂对照支撑（普通文件 OK + `mkfifo` EPERM + `bind` EPERM + 抽象命名空间 OK）。

对本包的后果：`add_unixsocket()` 只做
`mkdir(dirname)` → `unlink` → `bind(sock, sun_path=device)`，
`-d` **只接受文件系统路径**，没有抽象命名空间入口 ⇒ **输出通道在本平台建不起来**，
且换路径**无法**修复（表里 8 个落点全灭）。要出功能须改上游代码支持抽象套接字
（或改走 TCP），属**路径 C**，未自行开跑。
另：`add_unixsocket()` 在 `getpwnam`/`setgid` **之前**执行，所以即使权限问题解决，
仍会先死在 bind。

**实测更正（真机跑打包出的 `inputlircd` 得到的第一条真错）**：
`main()` 先开设备，一个都打不开时直接
`Unable to open any event device!` 退 `EX_OSERR(71)`，
**根本走不到 `add_unixsocket()`**。
⇒ 三条墙的**首要约束是墙一（evdev DAC）**，墙三在其下游，
用守护进程本身**观察不到**。因此 §4 的 C1 改用
`test_package/unix_bind_probe.c`（同工具链编译的消费者探针）**复刻**
`add_unixsocket()` 的 `bind()` 语义来取证，
而不是拿守护进程的日志当套接字证据——后者的读数实际来自墙一。
另记：`open_evdev()` 的失败详情走 `syslog(LOG_ERR, …)`，在本机 **不落 stderr**
（`openlog(..., LOG_PERROR, ...)` 未把消息带到标准错误），
所以断言一律不押 syslog 文本，只押 `fprintf(stderr, …)` 的那几条。

### 3.4 顺带核（控制终端）

| 探针 | 结果 |
|---|---|
| `open("/dev/tty")` | **ENXIO(6)** |
| `open("/dev/ptmx")` | **OK** fd=3 |

本包不使用控制终端（源码无 `/dev/tty`、无 `ctermid`、无 `TIOCSCTTY`），
此两行只作同机口径记录，**不外推**成"OHOS 不支持 tty"。

## 4. 测试账本（赛道二）

**上游四种形态逐一自数**（取证：`tar tzvf inputlirc_34.orig.tar.gz`、`grep -nE '^tests?:\|^check:|^installcheck:' Makefile`、`find . -iname 'tests*' -o -iname 'RUNTEST*' -o -iname 'examples*'`）

| 形态 | 命中 | 说明 |
|---|---|---|
| 独立测试框架（`make check`/ctest/autotools TESTS） | **0** | `Makefile` 目标只有 `all/install/install-sbin/install-man/install-service/clean`，`.PHONY` 同 |
| 语料目录（`tests/`） | **0** | `.orig` 仅 6 个文件，无目录 |
| RUNTEST/dejagnu 脚本 | **0** | 无 |
| 示例目录（`examples/`） | **0** | `gennames` 是构建期 `names.h` 代码生成器，**不是**测试 |

**五维账本**（消费者断言，`test_package/test_inputlirc.sh`；W4 r1 判决后的口径）

| 维度 | 数 |
|---|---|
| 静态总数 | **8** |
| 可执行数 | **8** |
| 实测通过数 | **8** |
| 跳过数 | **0** |
| 失败数 | **0** |
| 平台观测（**不计入** `assertion_count`） | **1** |

上游测试：总数 0 / 执行 0 / 排除 0 / 通过 0 / 失败 0 —— 如实记 0；测试面由 `test_package` 补齐 **8 条产物断言 + 1 条平台观测**。

**★W4 r1 降级理由（P2）**：原 C1 的证据对象是**平台**（自建 `unix_bind_probe` 复刻 `add_unixsocket()` 的 `bind()` 语义），它既不执行也不链接 `inputlircd` ⇒ 属**被测对象之外的自证**，故移出 `assertion_count`，改记为**平台观测 O1**（脚本里走独立的 `obs()` 与 `OBSERVATIONS_*` 计数，输出前缀 `[OBSERVE]`，与 `[PASS]` 不撞）。R34 本身仍由 CI 的 L1e 破坏性反向验证满足（`reused-from-w4r1`：`reports/w3-local-ci.log` 的 `[sabotage] bin/ moved away → Negative test confirmed`），本轮因此**不判 R34 违规**，只降级分类。

**同源五处（逐字 = 8）**：① `test_package/MANIFEST.yml` 的 `assertion_count/static_total/executable/measured_pass/skip/fail` 六字段（另单列 `platform_observations: 1`）；② `test_package/test_inputlirc.sh` 的 `if [ "$TOTAL" -lt 8 ]` 下限；③ `test_package/conanfile.py` 的 `REQUIRED_ASSERTIONS = 8`；④ 本节五维表；⑤ 两级 `manifest.yaml`——版本级 `34/manifest.yaml` 新增的 `upstream_tests:`/`test_package:` 块与软件级 `archives/i/inputlirc/manifest.yaml` 的 `versions."34".tests` 行。

**可证伪性**（本仓抓过 qperf"两分支都记 ok"与 proda"汇总行早于自检"，此处规避）：
产物断言计数器只由 `ck()`/`ckf()` 内部按 `rc` **且** 输出文本双条件递增，
无手写 `OK=$((OK+1))` 分支；任一条不满足即 `[FAIL]` 且末尾 `exit 1`；
末行汇总在全部断言之后才打印。每条断言**同时**钉住退出码与上游诊断原文
（`EX_USAGE=64` / `EX_OSERR=71`）。平台观测 `O1` 走 `obs()` 的独立计数器，
不并入 `ASSERTIONS_*`；**探针缺失时脚本直接 `exit 1` 硬失败、不静默跳过**，
平台若哪天放开文件系统 `bind()`，`O1` 打印 `[OBSERVE-DIVERGED]` 把事实变化
暴露在同一份日志里，但按定义它不是产物断言，不翻转判决。

断言清单（8 条产物断言，逐条钉退出码 + 上游诊断原文；O1 平台观测单列在表后）：

| # | 断言 | 钉住的事实 |
|---|---|---|
| A1 | 打包出的 `inputlircd` 存在且可执行 | 安装布局 / `bindirs` |
| A2 | `-h` → rc=64 + `Unknown option!` | CLI 解析（上游无 `-h`） |
| A3 | 裸调用 → rc=64 + `Not enough arguments.` | 参数校验 |
| B1 | `-f -d … -n '*'` → rc=71 + `No event devices found!` | §3.1 `glob` GLOB_NOMATCH |
| B2 | `-f -d … /dev/input/event0` → rc=71 + `Unable to open any event device!` | §3.1 evdev DAC（首要约束） |
| D1 | `-u nosuchil34user …` → rc=71 + `Unable to open any event device!` | 启动顺序：开设备先于降权与建 socket |
| E1 | `<pkg>/share/man/man8/inputlircd.8` 含 `inputlircd` | 打包布局 |
| E2 | `<pkg>/lib/systemd/system/inputlirc.service` 含 `inputlircd` | 打包布局 |

**O1 · 平台观测（不计入 `assertion_count`）**：`test_package/unix_bind_probe.c` 用同一 clang 工具链编译，复刻 `add_unixsocket()` 的文件系统 `bind()` 与抽象命名空间 `bind()`，断言"文件系统端点 EPERM(1) + 抽象命名空间 OK"这一组合（实测 rc=0 + `VERDICT: filesystem unix-socket bind refused`）。它测的是**平台能力**、不是产物行为，故按 W4 r1 判决单列；行为变化时打印 `[OBSERVE-DIVERGED]`。

## 5. 适配路径与知识库声明（3+2）

**适配路径**：路径 A（配方 + 可移植性补丁），功能面受限按 §3 分层申报
**使用知识库**：E051（syscall 面逐号 SIGSYS 家族）、E024（AF_UNIX bind 受限）、
E091/E119（`linux/*.h` 与 `sys/socket.h` 头冲突，本包未触发）、E097（无 configure 的手写 Makefile 手工安装）
**知识库扩展**：1 条已落盘（机制 (b)）——`knowledge/drafts/DRAFT-inputlirc-34-hardcoded-usr-include-uapi-path-resolved-via-clang-M.kv` + 同名 `.md`，本 PR 内成对交付；(a)(c)(d) 判 hit、见下不另立
- **关联 Issue**：**#3360 已创建** —— https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3360 （标题【知识库扩展】inputlirc 34：上游把内核 UAPI 头写成绝对路径 /usr/include/linux/*.h，而鸿蒙 PC 上 /usr/include 整棵不存在；正文已含一手探针读数、六个同族前例的差异化定位与作用域边界）

### B 判定（主窗按 W4 r1 定案，本棒落盘）

四范围查重结果取审计复算（`reused-from-w4r1`，判决件 `b_determination`）：
`knowledge/graph/*.kv`（540 条）、`knowledge/graph/index.tsv`、`knowledge/drafts/*.kv`（2920 份）、
`archives/**/notes.md`。四档候选逐一落判：

- **(b) §1 绝对 `/usr/include` UAPI 头 → 判 `create`，已按主窗裁定成对落盘**：
  `knowledge/drafts/DRAFT-inputlirc-34-hardcoded-usr-include-uapi-path-resolved-via-clang-M.kv`
  + 同名 `.md`（本 PR 内交付，过 `yaml.safe_load` 与 `scripts/ohc-run.py draft-review`）。
  差异化定位（第 4 范围 6 个同族前例为何不算同一机制）写在草稿的
  `related_drafts`/`.md` 的定位表里：`bridge-utils/1.5`（`--with-linux-headers=<sysroot>/usr/include`
  是 configure 选项）、`bird/3.1.6` 与 `bird2`（`-I$SYSROOT/usr/include` 追加 CPPFLAGS）、
  `aliki/0.3.0` 与 `audtty/0.1.12`（补丁**删掉**硬编码 `/usr/include`）——四条前例都发生在
  "头目录可作为编译选项增删"的层面；本包是**内核 UAPI 头被写成绝对路径**，既是 `make` 的
  **前置条件**（`names.h: /usr/include/linux/input-event-codes.h`，症状是
  `make: *** No rule to make target ... needed by 'names.h'`）又是源码里的尖括号绝对包含，
  处置是**参数化 + 问编译器 `clang -M` 反解真实 sysroot**，症状签名与解法都未被覆盖。
- **(a) 补丁 0003 `GLOB_NOMAGIC` → 判 `hit`，不另立**：按文件名引用
  `knowledge/drafts/DRAFT-ohos-musl-glibc-specific-symbols.kv/.md`
  （同根因 musl 不提供 glibc 扩展、同层次编译期符号缺失且报错正是
  `use of undeclared identifier`、同处置无条件纯 C 兜底且禁平台宏 R8、同作用域按 glibc 写
  在 musl/OHOS 上构建 ⇒ hit 四条件全中）。增量只作披露：兜底为 0 后对不存在的字面 `-n` 参数，
  诊断从"打不开该设备"变"没有设备"；上游行位实测 pristine 第 497 行（补丁后 506），
  `conandata.yml` 的 `patch_description` 已写 `:497`，**准确**。
- **(c) §3.3 AF_UNIX 文件系统端点 `bind()` EPERM → 判 `hit`，不另立**：
  `knowledge/graph/E024.kv:17-20`（SELinux 限 `bind`）+ 草稿
  `knowledge/drafts/raul-2.0.0-af-unix-bind-blocked-meson-skip.kv`
  （原文已记"可写目录仍 EPERM=1、改路径无法修复、属平台能力缺失"）
  + 第 4 范围 `archives/d/dbus-glib/0.114/notes.md:57` 的四臂矩阵（`/tmp`=EROFS、
  `$HOME/tmp`(hmdfs)=EPERM、`/dev/shm`=EACCES、abstract=OK）与
  `archives/d/daemontools-encore/1.11/notes.md:31`（`mkfifo`/`mknod` 亦 EPERM
  ⇒"拒创建非常规 inode"这一总归因也已有原文）。本包增量是机理刻得更细，
  建议以 E024/raul 草稿的**补证与边界细化**处理，是否 promote 由主窗定。
  ⚠ **不引 E521**：审计已把工具给的 `hit(E521)` 否证为假阳性（E521 是 libtoolize 硬编码
  `sed` 致 `ltmain.sh` 落父目录，本包裸 `make`、无 autoreconf/libtool），故本文与草稿都不出现 E521。
- **(d) §3.2 `setreuid/setregid` SIGSYS → 判 `hit(E051)`，只作边界细化**：
  E051 原文已写"**部分** syscall 的 SIGSYS 不可捕获"，故本包的"非整族"结论已在条目内；
  `knowledge/drafts/DRAFT-ohos-syscall-capability-matrix-fork-probe.kv` 也已把
  "逐 syscall fork 探测 + 能力矩阵三态"作为机制主张 ⇒ 再立即重复。
  对外结论**不得**写"setuid 族整族可用/不可用"，须逐号列（§3.2 表已如此）。
- **§2 无 `install(1)` 且 `cp` 无 `-m` → 判 `none`（环境事实）**：属镜像缺件而非平台行为，
  不升 B；已扫 E312/E313/E490/E514 与 4 份相关草稿标题，未逐条读原文确认语义。

**R40 判据出处（主窗按 W4 r1 裁定"可交付，但必须先补条件"，此处留引用）**：
`SKILL.md:351` 的 R40 原文"**深度适配库需验证适配完整性**：……需检查实质性平台适配代码（非 stub/return 0）"；
`templates/audit-prompt.md:29`"R34/R9/R8/R19/R40 欺骗类 ⇒ **阻断（P0/P1）**、命中即 verdict=fail"、
`templates/audit-prompt.md:76` P0 定义"空壳测试/伪造状态/伪造 sha256/……/审计文件与实际矛盾"。
本包有 3 枚真补丁、补丁新增行平台宏命中 0（复算：`grep -nE '^[+].*(__OHOS__|__linux__|__MUSL__|__MACH__)'
archives/i/inputlirc/34/patches/*.patch` → 空，`reused-from-w4r1`）⇒ **不属**掏空型，R40 未被违反。
同形先例（已合入 main）：`archives/d/dbus/1.14.10.2/notes.md:32`、`archives/d/daemontools-encore/1.11/notes.md:31`、
`archives/b/bcc/0.37.0/notes.md:234`。


## 6. 未做 / 风险

- evdev `ioctl` 面（`EVIOCGVERSION/EVIOCGBIT/EVIOCGNAME/EVIOCGRAB`）**未执行**：
  无可用 event fd，需 root 或 `input` 组成员身份 ⇒ 申报口径"未执行 + 证据"。
- `inputlircd` 端到端功能（设备→socket 事件流）**未验证**，卡在 §3.3 的输出通道。
- `.orig` 包内**无 LICENSE 文件**，`license = "GPL-2.0-only"` 依据是各源文件头部声明；
  配方因此**不** `copy(COPYING)`（上游没有这个文件，硬 copy 会失败）。
- `inputlirc.service`（systemd 单元）按上游 `install-service` 装进
  `<pkg>/lib/systemd/system/`，HarmonyOS 无 systemd，该文件对运行无作用，仅为打包完整性保留。
- **homepage 字段（W4 r1 P1 整改）**：三处机器可读字段原写 `https://www.sliepen.org/inputlirc/`，本窗 `/usr/bin/curl -s -o /dev/null -w "%{http_code}" -L` 实测：
  `https://www.sliepen.org/inputlirc/` → **404**（审计复算另 4 种写法全 404，`reused-from-w4r1`），同站根 `https://www.sliepen.org/` → **200**；
  本窗把字段改为发行版元数据声明的值 `https://git.sliepen.org/inputlirc`（Debian `d/control` 的 `Homepage`），并**自己 curl 一次**：**无斜杠与带斜杠两种写法本窗实测均为 404**。
  ⇒ 如实陈述：**该字段取自 Debian 元数据、本窗实测 404，不得表述为"官网可用"**。换址理由不是"它可用"，而是"它是权威发行版对本项目主页的唯一声明，且原 URL 已确证 404"；若主窗另有权威 200 地址，替换即可（三处字段与本节须同步）。
  附带：R39 源码官方性**不受影响**——`.orig` 取 `deb.debian.org` 权威归档（判据见 §7 末 R40 段）。
- **上游缺陷（④类，未致错、未改）· 20 条 `-Winitializer-overrides`**：`names.h` 由 `gennames`
  生成，别名同码互相覆盖（首条 `KEY_DISPLAYTOGGLE` ≡ `KEY_BRIGHTNESS_TOGGLE`，
  `names.h:782/781`）。`-Winitializer-overrides` 命中数**恰为 20**，且是该次编译**唯一**的告警类型
  （`reused-from-w4r1`）。现象只有在 KERNELINC 打通、`names.h` 真能生成后才第一次可见。
  后果：C 稀疏数组初始化器的字典项后者覆盖前者 ⇒ 别名字典项只保留最后一个，未致编译/运行错误。
  复算命令：
  `KI=<sysroot>/usr/include; make names.h KERNELINC=$KI && clang -c -Wall -g -O2 -I$KI inputlircd.c`
  ⇒ compile rc=0、`grep -c initializer-overrides <log>` = **20**、`[-W...]` 种类统计仅此一项。
  是否向上游报 Issue 由主窗定，本棒不改上游代码。
- **E490（配方侧处置，未进 notes 的补记）**：解包后脚本可能丢可执行位（HMDFS 上 `chmod` 不总持久），
  上游 `Makefile` 以 `./gennames` 调用 ⇒ `conanfile.py:109` 显式
  `os.chmod(os.path.join(self.source_folder, "gennames"), 0o755)`。
  因此 `reports/conan-verify-report.md` 里"已知风险 E490 未在配方中处理"一行是**检查器假阳性**
  （漏看 `os.chmod`），不改判据、只披露（见 §7）。
- **许可（R16 口径）**：`.orig` 6 个文件实测**无 LICENSE/COPYING**，`license = "GPL-2.0-only"` 的
  授权依据是**各源文件头部声明** ⇒ 配方**不** `copy(COPYING)`（上游没有该文件，硬 copy 必失败），
  软件级 `README.md` 的许可行同口径陈述。编号出处：W4 r1 判决件 CHK-11 与本棒任务书 §2 第 10 条；
  本窗在 `SKILL.md:340` 只找到 R16-R20 的合并行（协作与打包），**未定位到独立的许可条款原文**，
  故此处只登记编号出处、不改写规则文本，需主窗确认。
- **补丁必须按 0001→0002→0003 顺序应用**：`0003` 的 hunk 以 `#include <linux/input.h>`
  为上下文，那是 **0001 的结果** ⇒ 在 pristine 树上单枚 `git apply --check` 必失败
  （实测 `error: patch failed: inputlircd.c:43`；`0001`、`0002` 单枚 `--check` 均 rc=0）。
  `reused-from-w4r1`（三枚顺序应用 rc=0、逆序 `-R` 还原 rc=0、`diff -r` 与未触碰解包全等）。
  三处计数一致：`conandata.yml` 3 条 = `34/manifest.yaml` `patches_applied` 3 条 = `patches/` 3 枚。
  消费方不得单独挑用 0003。

## 7. 未转绿 / 框架存量红（只披露、不改判据）

**口径**：以下为框架/判据的存量矛盾，本棒**不删脚本、不改判据、不为过检查改文本**，逐项带
判决行原文与出处。`reused-from-w4r1` = 审计判决件 `~/tmp/uc2/z32-inputlirc-w4/bundle/finish.out`；
本轮复跑的同名读数行号在提交②（`finish` 之后）回填。

| 项 | 判决行原文 | 出处 |
|---|---|---|
| finish 外层 rc 与内部 EXIT_CODE 并存 | `║ EXIT_CODE: 0 (知识整理已完成)` / `║ STEP_FAILED: Step6` / `RC=1  (step: python3 scripts/ohc-run.py)` | bundle/finish.out:117,118,130 |
| 失败步骤列表 | `⚠️    失败步骤: step5b, step8` | bundle/finish.out:103 |
| step5b 知识引用闸（全仓 4623/4997 = 92.5% 存量矛盾，手册/04 §11.5(2) 口径为"披露即可"） | `ℹ️ manifest.yaml: knowledge_count=5 unreferenced=5` / `⚠️ ⚠️ 存在知识遗漏: pending=0 failed=0 unreferenced=5` | bundle/finish.out:88,89 |
| step8 gen_summary 框架缺陷 | `⚠️   gen_summary 失败: 'str' object has no attribute 'append'` | bundle/finish.out:92 |
| Step3 G0 原始包定位 | `❌ G0: 找不到原始 tarball` / `⚠️ G0 干净构建验证失败，请手动检查构建结果`（同段另有 `✅ G0: PASS` 的知识图谱预查询，两者不是一回事） | bundle/finish.out:24,25,36 |
| Step1 源码目录定位 | `❌ 无法定位源码目录: orig=None, work=None` | bundle/finish.out:10 |
| step10 三缺件与一致性 | `⚠️   .staging-verified 缺失` / `⚠️   ❌ .staging-verified — 需创建 .staging-verified 空文件` / `⚠️ ⚠️ finalize 完成，有 2 个缺失 + 1 个一致性问题` | bundle/finish.out:4,99,67 |
| L2 版本/help 探测 | `L2_RESULT=skip: inputlircd version/help failed` | `reports/w3-local-ci.log:393`（**框架预期**：CI 裸跑 bin 不载 runenv ⇒ 既非失败，也不得当"可执行证据"引用） |
| conan-verify 的 E490 假标 | `⚠️ 已知风险 E490 未在配方中处理` | `reports/conan-verify-report.md:11`（检查器漏看 `conanfile.py:109` 的 `os.chmod`，见 §6） |
| 判绿图标可能与文字相反 | `**Verdict**: PASS` 与 `## G0: ✅ PASS` 分列 | `reports/conan-verify-report.md:3,8` ⇒ 本包判绿一律要"文字 PASS + `**Verdict**` 行 + rc"三一致 |
| PF7 源 URL 闸（R39） | `✗ PF7 源URL闸(R39): archives/i/inputlirc/34/conandata.yml:5 Debian 下游重打包源`（另有 `34/manifest.yaml:13` 同项、`34/manifest.yaml:32` 绝对本地路径） | `python3 scripts/ohc/preflight.py . origin/main HEAD` 改前 rc=1 |
| PF9 路径闸与软件级三件套互斥 | `✗ PF9 分支/路径闸: 变更路径缺版本目录层（须 archives/<字母>/<包>/<版本>/<文件>）——CI 将报 No packages to build（490 例）: archives/i/inputlirc/README.md, archives/i/inputlirc/commands.json, archives/i/inputlirc/manifest.yaml` | 同上。这三枚文件是 R38/R28 要求的**软件级**三件套，PF9 却要求一切变更都落在版本目录层 ⇒ **两条判据对本包互斥**，本棒不删必需文件，只披露 |

**R40 名下的未执行面**：未提权、未试装 setuid-root 绕过、evdev `ioctl` 四号
（`EVIOCGVERSION/EVIOCGBIT/EVIOCGNAME/EVIOCGRAB`）**未执行**、端到端事件流**未验证**
（卡点见 §3.1/§3.3），申报口径为"未执行 + 证据、分母不缩"。
**本轮复跑（提交②回填）实测行号** —— `archives/i/inputlirc/34/reports/w3-local-ci.log`：检查模式→71 行；JC_RESULT=pass→90 行；ASSERTIONS_TOTAL=8→369 行；OBSERVATIONS_TOTAL=1→372 行；[OBSERVE] O1→365 行；L2_RESULT=skip→393 行；sabotage Negative→387 行；`.ci-result.json` 与 `conan-verify-report.md` 见 §7 表末与 GATES.md。

---

## 8. W4 r2 定向复审与本轮收口（主理-32，2026-09-25 05:50）

**判决件（随 PR 入库）**：`archives/i/inputlirc/34/reports/audit-result.json`（`git add -f`，
设备原件 `~/tmp/uc2/z32-inputlirc-w4r2/audit-result-feat-inputlirc-34-r2.json`，两端字节数一致）。
判决 `verdict=pass`、`submit_allowed=true`、**P0=0 / P1=0 / P2=2 / P3=4**，绑定
`head_sha=dad79acb26b8615329fbe67b89c555f7266b7300`（r1 判决件仍在 `~/tmp/uc2/z32-inputlirc-w4/`）。

**两条 P2 与三条 P3 的处置（提交 `2fcc505366`）**：

| r2 项 | 处置 | 落点 |
|---|---|---|
| R2-A1（P2）配方三处：未用 `Autotools` 导入、`clang -M` 续行折叠替错对象、解析失败静默回落 `/usr/include`（与本 PR 草稿的禁止做法互斥） | 三条全改：删导入、`replace("\\\n", " ")` 折真续行、`os.path.isdir("/usr/include/linux")` 判过才用否则 `raise ConanInvalidConfiguration` ⇒ 实物与草稿禁例同源 | `conanfile.py:5,73,79-90` |
| R2-A2（P2）探针指针错位（`probe0.txt:22-32` 实为 mount 表） | 改引 `:39-46`（判别性 open() 读数所在） | `notes.md:92` |
| R2-C1（P3）"节点存在性不可判定"未加通路限定 | 归因改题为"经 `/dev/input` 的 open()/glob() 在本 uid 下不具判别性"，并补入 r2 正面证据（`access("/sys/class/input/event0")=0` vs `event9137=ENOENT`、`/proc/bus/input/devices` 列出 `event0…event16`）⇒ 节点确存在，"内核无输入设备"这一竞争解释被排除 | `notes.md:91,95`、`README.md:54` |
| R2-C2（P3）重复句 + `L2_RESULT` 行号自相矛盾 | 删重复行；两处统一为 `w3-local-ci.log:393` | `notes.md:94,368` |
| R2-C3（P3）`conan-create.log` 被 finish 复跑覆写致旧行号失效（该件未 tracked） | **不改提交态**，只把引用一律改锚 `reports/w3-local-ci.log` | 本节与 §7 |
| R2-C4（P3）`draft-review` 报 `root_cause=❌缺` | 判为 `.kv` 块标量被读空的**框架假阳性**，不改稿（`safe_load` 51 键含 `root_cause`） | 判决件 |

**整改后复跑（本轮实测，提交 `2fcc505366` 之后）**：
`python3 scripts/ohc-run.py finish inputlirc 34 built`（外层 rc=2，`失败步骤: step5b, step8`，
均为 §7 已披露的框架存量项；`EXIT_CODE: 0`、终态 `built`）——
`reports/w3-local-ci.log` 23276 字节 @05:49、`检查模式: incremental (17 个文件)`→71 行、
`JC_RESULT=pass`→90 行、`[OBSERVE] O1`→365 行、`ASSERTIONS_TOTAL=8`→369 行、
`OBSERVATIONS_TOTAL=1`→372 行、`L1_RESULT=pass`→392 行、`L2_RESULT=skip`→393 行、
`Success: 1`→401 行、`Pass rate: 100.0% (1/1)`→403 行；
`conan-verify-report.md` `**Verdict**: PASS`（:3）且 `## G0…G4: ✅ PASS`（:8,17,31,37,40）；
`.ci-result.json` 六字段 `step=W3_local_ci exit_code=0 timestamp=2026-09-25T05:49:57.499954`，
`integrity_hash=cf7645800877a94a` 与按 `sha256('<timestamp>:inputlirc:34:0')[:16]` 复算**相等**，
`log_sha256=5dcbdde0b15ec5c4…` 与 `reports/w3-local-ci.log` 实算 sha256 **相等**（强于 md5 的绑定）。

**仍红的静态闸与不修的理由**（`python3 scripts/ohc/preflight.py . origin/main HEAD` → rc=1）：
① PF9 把软件级三件套（`archives/i/inputlirc/README.md`、`commands.json`、`manifest.yaml`）判成
"缺版本目录层"，与 R38/L0k 的必需文件互斥 ⇒ 属框架侧缺陷，本棒不删必需文件；
② PF7×2（`conandata.yml:5`、`34/manifest.yaml:13`）——上游 `git.sliepen.org/inputlirc` 无可下载
归档：r2 审计者自建 curl 复算带/不带斜杠均 404、cgit 五种路径与三种 snapshot 拼法全 404、
`?repo=` 只回 1 字节、`ls-remote` 取不到 refs、GitHub 镜像形态 404 ⇒ **不存在同 sha256 的官方
https 归档**，故取 Debian 权威存档的 `.orig` 原样上游包（sha256 与 Debian 索引逐字节一致），
按 R39"官方正式源或权威镜像源"口径交付并在此登记为例外。
`conandata.yml` 盘上与提交态一致（禁词命中 0，无镜像注入残留）。

---

**编译结束**: 2026-09-25 05:48
**最终状态**: built
