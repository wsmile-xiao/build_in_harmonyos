# toybox 0.8.9 适配笔记

## 编译环境

- 设备：HarmonyOS PC（aarch64，OHOS），唯一执行设备；任务 worktree `~/qzy/hw-6-toybox-0.8.9`，分支 `feat/toybox-0.8.9`。
- 工具链：clang（profile `ci/conan/profiles/ohos-aarch64`），构建全程 `make -j1`（见下 HMDFS 条）。
- Conan 2.29.1（OHOS 适配版），独立 `CONAN_HOME=~/tmp/ch/home-hw-6-toybox`，`remotes.json` 从已验证 home 复制。
- 取包：`https://www.landley.net/toybox/downloads/toybox-0.8.9.tar.gz`，sha256 `06913dde3de7139b40f947bd7f23869dfc8796e9c6ff39de02719f8b7b2d47ad`（官方站点 HEAD 200 实测 3517516 字节）。conandata 只保留这一条官方 URL，无镜像。

## 软件概述

toybox 把 GNU/BSD 常用命令打包进单个 multi-call 二进制（0.8.9 收录三百余个 applet）。本包 `package_type=application`，交付物是 `bin/toybox` 一个静态链接的可执行文件，配套 `archives/t/toybox/commands.json` 声明命令面（R38）。

## 编译步骤

1. `source()`：`get(self, **conan_data["sources"], strip_root=True)`。
2. `build()`：先 `apply_conandata_patches`，再把 `configure` 与 `scripts/` 下所有 `#!/bin/bash` 的 shebang 改写为 `tool_requires("bash/5.3")` 的绝对解释器路径（改写数为 0 时抛错，防上游布局变化后修法静默失效），然后 `make CC=<target> HOSTCC=<host> CROSS_COMPILE= NOSTRIP=1 LDFLAGS=-static defconfig` → 同一组变量 `make`；产出 `toybox` 后在 `build()` 内**真实执行上游套件** `TEST_ALL=1 VERBOSE=all bash scripts/test.sh`，并把每条失败落台账按族归账（§10 硬规则，不跳过上游入口）。
3. `package()`：只拷 `toybox` 到 `bin/`、`LICENSE` 到 `licenses/`，并按 E543 显式 `chmod 0755 bin/toybox`。
4. `package_info()`：`bindirs=["bin"]`，`includedirs/libdirs/libs` 全空（本包无库无头），并向 `buildenv_info`/`runenv_info` 追加 `PATH`，使消费者能直接调用 applet。

## 关键构建参数说明

- `CC`/`HOSTCC` 必须显式给：toybox 的 `Makefile`、`scripts/kconfig`、`scripts/portability.sh` 三处都按默认 `cc` 取宿主工具并做编译器存在性探测，OHOS 只有 clang、无 `cc`，探测失败即 `No cc found` 退出 1。交叉构建下 `HOSTCC` 另需 `CC_FOR_BUILD`（mkflags/mktags/config2help/instlist 这些 host 生成器必须能在本机跑起来）。
- `LDFLAGS=-static`：OHOS 的共享 `libc.so` 不含 `getspnam`/`getspnam_r`（只在 `libc.a`），shadow-passwd 类 applet 只有静态链接才成立。
- `NOSTRIP=1`：保留链接期生成的 ELF，供后续代码签名流程处理，不在构建期剥掉符号。
- `make -j1`：HMDFS 不允许 `mkfifo`（EPERM），GNU make 的 jobserver 建不起来，`-j>1` 只会报警后退化成串行。
- `CROSS_COMPILE=` 置空：上游 Makefile 默认按交叉前缀取工具，本机工具链无前缀。

## 遇到的问题与解决方案

| 现象 | 根因 | 处置 |
|---|---|---|
| `scripts/genconfig.sh: No such file or directory` | 缺的是解释器不是脚本：所有驱动脚本 shebang 写 `/bin/bash`，本平台无 `/bin/bash`（CI worker 在 `/data/service/hnp/bin/bash`） | 构建前把 `configure` 与 `scripts/` 下的 shebang 改写为 `bash/5.3` 包内绝对路径；`tests/*.test` 不改（harness 只 source、不 exec）；改写数为 0 即抛错 |
| `No cc found`（构建期与测试期同点死） | 三处按默认 `cc` 探测编译器/host 工具 | 显式 `CC`/`HOSTCC`，交叉时要求 `CC_FOR_BUILD` |
| `make: jobserver mkfifo: ... Operation not permitted` | HMDFS 不支持 mkfifo | 固定 `-j1`，不靠 `-j` 并发 |
| 链接期 `getspnam`/`getspnam_r` 未定义 | OHOS 共享 `libc.so` 无这两个符号，只有 `libc.a` 有 | `LDFLAGS=-static` + 补丁 `0002-ohos-utmpx-shadow-declarations.patch` 声明 OHOS musl 头缺的 utmpx/shadow 入口 |
| 打包后的 `bin/toybox` 在设备上没有可执行位 | E543：HMDFS 默认文件模式 660 | `package()` 内 `chmod 0o755` |
| 上游套件静默漏跑 | `test.sh` 默认跳过没有可执行位的 `.test`，而 HMDFS 模式位不可靠；首个失败还会打断整轮 | `TEST_ALL=1` 强制全清单、`VERBOSE=all` 跑完 118 个文件 |
| 台账把失败原因报错 | 同一 applet 可命中多个机制（tar 既有 `bad group sys` 账户族又有纯 mode 模板族；find 同时有 fifo/mode/`-printf` 转义三种） | 具体族按证据先匹配、通用值差异族垫底；名字对而上下文不含该族签名一律判未定性并中断构建 |

## 上游测试口径（三个方向分别记账，不互相冒充）

- `N_static = 1952`：118 个 `tests/*.test` 里 `testcmd`/`testing`/`txpect` 注册语句行的逐文件计数（可 grep 复核，不含循环展开）。
- `N_executed = 1703 = pass 1330 + fail 325 + skip 48`：本次 config 下真实执行项。
- 静态与执行之间约 249 的净差由两个**相反方向**构成：循环展开使执行项多于注册行（约 +282，`chmod` 6→154、`chattr` 7→15、`date` 35→40、`file` 24→29、`cut` 25→28 等）；同时 21 个 `.test` 因 applet 未编入本次 config 而**整文件 0 执行**（531 条，逐字机制 `scripts/test.sh:43`，只留一行 `SKIP: <name> disabled`；其中 `sh` 266 行、`expr` 43、`dd` 42、`man` 37、`skeleton` 29（上游模板件）、`useradd` 14、`hexdump` 14、`unzip` 13、`demo_number` 12（上游演示件）、`diff` 12、`gzip` 11、`groupadd` 10、`getfattr` 6、`fold` 5、`groupdel` 5、`tr` 4、`getopt` 3、`xzcat` 2、`more` 2、`bc` 1、`vi` 0）。531 − 约 282 ≈ 249，与 1952 − 1703 吻合。
- 21 个 applet 未编入本次 config 不是"跳过用例"，也不是分母虚高：独立载体是用被测二进制自身的 applet 清单（`./toybox` 无参输出）逐个比对，21/21 查无、零反例。`sh`/`vi` 在 0.8.9 里被上游自标 incomplete，编入可能引入新的真实失败面，本次不预设开启。

## 325 例失败的族账（`accounted=325`、`unexplained=0`）

| 族 | 名称 | applet 与例数 | 逐字凭据 |
|---|---|---|---|
| F1 | HMDFS 权限位模板钉死 | chmod 152、chgrp 24、test 12、tar 10、mkdir 6、chown 5、find 3、cp 1、gunzip 1 = **214** | 文件系统按 mode 模板发放权限，上游断言的 4 位 mode 与实得不一致（如 `drwxr-x--- -> drwxrws--x`） |
| F2 | 无 hardlink | ln 4、mv 2、link 2 = 8 | `cannot create hard link from file1 to link1: Operation not permitted` |
| F3 | 无 FIFO | mkfifo 4、find 4、test 3 = **11** | HMDFS 不允许 mkfifo，夹具建不出来，结果只差文件类型字母 `p`（`dfLs` vs 期望 `dfLsp`） |
| F4 | OHOS 账户命名空间 | tar 46、id 4、find 1 = **51** | `tar: bad group sys`；`id` 多报服务组（1004 ueventd、1050 servicectrl、1051 powerctrl 等） |
| F5 | 特权设备 / ioctl / xattr | chattr 8、lsattr 7、setfattr 3、mount 2、losetup 4 = 24 | `losetup: -f: Permission denied`、`Inappropriate ioctl for device`、额外 xattr 命名空间 `user.hmdfs.perm`/`security.selinux` |
| F6 | statvfs 块大小 | du = 9 | 期望块大小 4/8、实得 8 |
| F7 | ARG_MAX 下限 | xargs = 2 | `xargs: argument too long`（131071B 处） |
| F8 | OHOS libc `strftime()` 尾部裸 `%` | date = 2 | `date: bad format %`；设备自带 0.8.12（动态链接）同样 rc=1，非本适配引入 |
| F10 | `find -printf` 转义差异 | find = **1** | 含 c 截断的期望输出与实际字节流不一致，属格式化行为差异而非权限限制 |
| F9 | `sed` 对 NUL 的行为差异 | sed = **1** | 含 NUL 的输入（`printf 'one\0two'` 交给 sed 做 `s/t/x/`）在 0.8.9 与设备 0.8.12 上逐字节相同（均未替换），而同输入 `tr` 正常 |
| R1 | **上游用例时序竞态（单列，不冒充平台语义）** | pidof = 2 | 逐字 `kill: (<pid>) - No such process`：`tests/pidof.test` 的子进程靠 stdin 阻塞存活，harness 喂空 stdin 使子进程先 EOF 退出，`pidof` 查无，测试自身的 `kill` 失败；绕开 harness 手工复现 `pidof -x` 正常返回子 pid，设备自带 0.8.12 对照同 rc=0 |
| 合计 | | **325**（323 平台/上游行为 + 2 上游用例缺陷） | 全部保留在分母内，不并入通过、不删用例 |

## 消费者测试（test_package，另列，不并入上游分母）

- 1 个消费者程序 `test_package/smoke.sh`，以打包后的 `bin/toybox` 逐条真实调用 applet 并比对精确输出，**12 条断言全部通过**（`SMOKE pass=12 fail=0`）：内容断言 10 条（basename 路径、seq 区间、`sort -n` 数值序、sha256sum 经 cut 取字段、`wc -l`、cut 字段、sed 首次替换、sort 字典序、`wc -w`、`head -n 2`）+ 失败路径 2 条（basename 缺操作数必须 rc=1；未知 applet 必须非零退出，实测 rc=127）。
- 断言的选择口径：每条都必须打到一个**确实编入本次 config** 的 applet。第一版误用了 `expr` 与 `tr`，而它们正是上面 21 个 0 执行 applet 里的两个，拿空输出去比对期望值必然失败；改测 `sort -n` 与 `wc -l` 是查过被测二进制自带 applet 清单后的选择。
- 内存预算 `max_rss_mb: 64`（toybox 是单文件小二进制，单条 applet 峰值 RSS 数 MB 级）。
- 迭代做法：改 `test_package` 后先用**已构建的真制品**直接回放 `smoke.sh`（不烧构建槽），绿了再进 `conan create`。

## 验证结果

- W3 真机 `conan create` 通过（含 `test_package`），本地 CI 模拟通过；G1 配方完整性 PASS、G0 知识图谱完整性 PASS（540 条）、JC 杂项文件 0。
- 上游测试在 `build()` 中真实全量执行，凭据行逐字为：`TOYBOX_TESTS files=118 static=1952 executed=1703 pass=1330 fail=325 accounted=325 without_errno_signature=227 unexplained=0 skip=48 rc=1`。`rc=1` 是 `test.sh` 对任何失败都返回非零的正常语义，配方的中断判据是"有未归因失败，或 rc 非零却一条失败都没记录（harness 自身崩）"，不拿 rc 当失败数用。
- W3 日志里的三行 `[fail] [Errno 2] No such file or directory: 'curl'` 属 CI 前置"pre-download"探针（该子环境 PATH 无 curl），框架随即回退 `will rely on conan's download`，实际取包由 conan 完成、G2 PASS，非本包缺陷。
- 证据位置：`reports/w3-local-ci.log`、`reports/conan-verify-report.md`、`reports/conan-create.log`；逐条失败台账 `upstream-test-ledger.tsv`（conan 构建目录内，路径在凭据行末尾打印）。

## 未执行 / 已知限制汇总

- 531 条注册语句（21 个 `.test`）因 applet 未编入本次 config 而整文件 0 执行，逐项名单见上。
- 325 例失败全部保留在分母内并逐条附原因，其中 323 例属平台能力/上游行为差异、2 例属上游用例时序竞态，均非本适配引入（每条都有设备自带 0.8.12 或手工复现作对照载体）。
- 48 条 `SKIP:` 是 harness 自己打的跳过记录，逐条原因在台账内，不计入通过。

## 源码修改

上游测试用例**零修改**、源码只有一条可移植性补丁 `patches/0002-ohos-utmpx-shadow-declarations.patch`（声明 OHOS musl 头缺失的 utmpx/shadow 入口，`strip: 1`，conandata 内带 sha256）。shebang 改写发生在构建目录的临时副本里，不进入交付 diff。
---

**编译结束**: 2026-09-29 20:49
**最终状态**: built
