# rungetty 1.2 适配笔记

## 编译环境

- 构建系统: makefile（上游只有一个裸 Makefile，18 行，无 configure / 无 autotools）
- 编译日期: 2026-09-25
- 编译器: `/data/service/hnp/bin/clang`（clang 15.0.4, `Target: aarch64-unknown-linux-ohos`），
  取自 conan conf `tools.build:compiler_executables`（R33，不硬编码、不读 shell `$CC`）
- 构建主机: A 机（HarmonyOS PC，`HongMeng Kernel 1.12.0` aarch64，真机编译+真机运行）
- Conan: 2.29.1，profile `ci/conan/profiles/ohos-aarch64`（os=OHOS os.version=6.0 arch=armv8）
- 状态: built（`conan-verify` G0–G4 + L2/L4/L5 通过，未 upload）

## 源码与获取

- 官方 URL（R39）: `https://ibiblio.org/pub/linux/system/serial/getty/rungetty-1.2.tar.gz`
- 归档: 15653 B，sha256 `5a2b7831b22f11b54f1d1fe1871068a82274d2ca961f577023afc76ed71b069a`
  （A 机 `curl` 实测 200 + 同哈希，2026-09-25 两次一致）
- 归档内容共 **8 个文件**：CHANGELOG COPYING Makefile README THANKS mingetty.comment
  rungetty.8 rungetty.c —— 无 tests/、无 `check` 目标、无 make 递归子目录。
- 交叉校验（仅作校验，**不写进 conandata/manifest**）：Debian 池
  `rungetty_1.2.orig.tar.gz` = 15618 B / sha256 `906c959e2e056128ce6c7d0b81724e58837c3907e3f86514741aef78be3b5a65`，
  与官方包字节不同（顶层目录名 + gzip 元数据），解包后 8 个文件逐文件 sha256 与官方包相同。
  ⇒ 采用官方 URL + 官方哈希，无需补丁或说明；池 URL 本身被 `scripts/ohc/preflight.py`
  的 PF7（Debian 下游重打包源）硬拦，不得出现在提交里。

## 编译步骤（配方实际执行的）

```bash
make CC="<conf 里的 clang>" -j1 rungetty      # 显式 rungetty 目标，见 P5
# package() 自行安装（上游 install 目标在本平台不可用，见 P3）：
#   rungetty    -> <pkg>/bin/rungetty            (0755)
#   rungetty.8  -> <pkg>/share/man/man8/         (FHS；上游是 $(ROOT)/usr/man/man8)
#   COPYING     -> <pkg>/licenses/
```

## 遇到的问题与解决方案（问题表）

| # | 症状 | 根因 | 最小复现 | 已试失败方案 | 最终方案 | 适用边界 |
|---|------|------|----------|--------------|----------|----------|
| P1 | `rungetty.c:316:36: error: use of undeclared identifier 'sys_errlist'`（共 7 处：316/433/449/464/478/482/608） | 上游用 glibc 的 `sys_errlist[]`；OHOS libc（musl 派生）的 `<string.h>` 即使给 `_GNU_SOURCE` 也不导出该符号 | `make CC=$clang`（pristine 源码）→ 第一条真实错误即上式 | ①`RPM_OPTS=-D_GNU_SOURCE`（**不解决** sys_errlist，反而**新增** `no member named '__domainname' in struct utsname`（rungetty.c:236）——`_GNU_SOURCE` 改变 `sys/utsname.h` 的成员可见性）②命令行注入 `-Dsys_errlist=…`（无对应符号可用） | 补丁 `patches/0001-libc-portability.patch`：7 处 `sys_errlist[errno]` → `strerror (errno)`（POSIX，语义等价，`<string.h>` 已包含） | 所有按 glibc 习惯裸用 `sys_errlist` 的老代码；musl/OHOS 一律不导出可见符号 |
| P2 | `ld.lld: error: undefined symbol: vhangup`（`>>> referenced by rungetty.c >>> rungetty.o:(open_tty)`） | OHOS libc **不提供 `vhangup()` 包装**；`<sys/syscall.h>` 里 `SYS_vhangup` 宏**存在**（值 58），但直接 `syscall(58)` 被**平台 syscall 过滤器拒绝并杀死进程**（SIGSYS=31，`Bad system call`，core dumped）——**不是** ENOSYS | 链接测试 `int main(void){return vhangup();}` → undefined symbol；探针 `raw_vhangup()`（fork 子进程里 `syscall(SYS_vhangup)`）→ `child TERMINATED BY SIGNAL 31` | ①`-D_GNU_SOURCE`（声明有、符号仍缺 → 仍 undefined symbol）②按号裸调 `syscall(446)`/`syscall(SYS_vhangup)` → **进程被 SIGSYS 杀死**（比编译失败更糟：运行期崩溃）③在补丁里用 `#ifdef __OHOS__` 屏蔽调用（**PF5 平台宏闸禁止** patches 新增行含 `__OHOS__`） | 同一补丁：`extern int vhangup (void) __attribute__ ((weak));` + 调用点改为 `if (vhangup) vhangup ();`。 libc 有该符号时行为与上游完全一致；没有时链接得到 `NULL`、跳过调用（上游本来就忽略返回值） | 任何"libc 未导出、且内核 syscall 被平台过滤器拒绝"的接口：**不能靠按号 `syscall()` 补（**证据 = 链接期对照 + 补丁**；本包消费者测试的 T4 只覆盖可达的五条调用路径，vhangup 调用点在 `open_tty()` 内 `ioctl(TIOCSCTTY)` 成功之后，非 root 且无 `/dev/tty1` 的构建主机到不了，故 T4 **不构成**对 vhangup 的运行时验证）**，必须弱符号可选化；见 本文件 `notes.md` 附录 A（真机原始读数全文）/ 附录 B（探针源码全文 + sha256）/ 附录 C（方法学自我更正） |
| P3 | 上游 `make install` 在本平台三重不可用 | Makefile 第 8–12 行：①`install -s -m 0755 **-o root -g root**`（非 root 必失败，且 `-s` 调 strip）②man 装到 `$(ROOT)/usr/man/man8`（**非 FHS**）③本平台**根本没有 `install(1)`**（`command -v install` → MISSING），`make install` 直接 `make: install: No such file or directory` (rc=127) | `make install DESTDIR=… ROOT= MANDIR=share/man` → 127 | ①命令行覆盖变量：Makefile **只有 `ROOT`（第 9–12 行）一个把手，没有 `PREFIX`/`DESTDIR`/`MANDIR`/`INSTALL`**，`-o root -g root` 与 `-s` 是写死的字面量，命令行去不掉②打补丁改写 install 目标：可行，但即便打好把手也仍缺 `install(1)`，装了个用不上的补丁 | **不改 Makefile**（零补丁）：由配方 `package()` 用 conan `copy()` 安装 `bin/rungetty` + `share/man/man8/rungetty.8` + `licenses/COPYING`，顺带完成 FHS 修正；man 页内容由 `man` 段落原样交付 | 裸 Makefile 且 install 目标写死 `install(1)`/root 属主的工具类包，在本平台优先"配方侧安装"而不是"给 install 目标打补丁" |
| P4 | `make: cc: No such file or directory` 类失败（OHOS 无 `cc` 别名） | Makefile 第 1 行 `CC=gcc`；镜像里既无 `gcc` 也无 `cc` | `make`（不传 CC）→ `clang: error` / `gcc: No such file` | 在配方里硬编码 `/data/service/hnp/bin/clang`（违反 R33 精神、换机即坏） | 命令行把手 `CC=`（第 1 行是普通赋值，可被命令行覆盖）：`make CC="{conf 取}"`，值来自 `tools.build:compiler_executables` | 所有裸 Makefile 包 |
| P5 | 上游默认目标 `all: rungetty` 之后紧跟 `size rungetty`（第 5–6 行） | 依赖 binutils `size`；设备上存在（`/data/service/hnp/bin/size`），但 CI 干净环境不保证 | `make` → 走到 `size` 步骤 | 忽略（赌 CI 有 size） | 配方显式构建 `rungetty` 目标（产物即二进制），不依赖 `size` | `all` 目标里混了信息打印步骤的老 Makefile |
⚠ 回退路径的证据口径（W4-r1 纠偏后）：本包 **未留存到** conan 打出「retrying with urllib」这类原始行的日志——强制重新 source 复跑一轮（logs/conan-verify-4-rerource.log）后，全文 grep urllib/retrying/rejected/content-encoding/x-gzip **命中 0 行**，说明该轮下载一次成功、未触发回退分支。故这条只作为**机制性说明 + G2 前后对照**（第 1 轮 conan-verify-1.log 的 G2: FAIL → 第 2 轮 conan-verify-2.log 的 G2: PASS，期间未改 sha256 与 URL）呈证，**不声称本轮实测触发了回退**

## 知识图谱命中（W0b / R11+R12）

- `G2` 首轮失败时引擎命中 **E540**（`shadow-ci / runner-path-prepend`，根因是 hnp 工具链 PATH 遮蔽）——
  与本轮症状**不同因**，属误命中（本轮是下载层，未进入编译），已按证据自行定位，未采纳其处方。
- 事后按机制检索命中既有草案 `DRAFT-conan-downloader-xgzip-content-encoding`（同机制、rec 直接可用），
  本包是它的**第二个实例 + 新症状变体**；另有 `E299`（Conan 源码获取失败分层诊断，
  `error_signature` 含 `sha256 hash failed for`）作家族条目。
- P2（`vhangup` 无 libc 包装 + 按号 syscall 被 SIGSYS 杀死）在本仓 `knowledge/` 与
  `适配经验汇总 / 经验库 / 适配检查清单 / OHOS行为探针清单 / B草稿库` 中检索
  `TIOCSCTTY / TCFLSH / TIOCCONS / vhangup / ctty` **均 0 命中**，属本轮新增读数（见下节）。

## 能力探针（OHOS行为探针清单 #5：pty/termios + 控制台 ctty 语义）

- 探针源码：`~/tmp/uc2/z42-rungetty/probe/probe_tty_ctty.c`（139 行，仅标准库/POSIX 头，不含任何三方库代码，
  即排除"包内问题"、证明是平台行为；为覆盖 正常路径 + 边界路径 + 返回码/errno 断言，超出清单的 30 行级模板，行数如实记 139）
- 编译命令（与配方同一套工具链）：`/data/service/hnp/bin/clang -Wall -Wextra -o probe_tty_ctty probe_tty_ctty.c`（rc=0）
- 待验证 SHA（探针源文件 sha256）：`b314a554239d8de32933ce96263755b49f7f18d21bb92b619812291306a0b3f9`
  （探针全文同时以代码块留在本文件 `notes.md` 附录 A（真机原始读数全文）/ 附录 B（探针源码全文 + sha256）/ 附录 C（方法学自我更正），随本包入库、跨机可取）
- 设备：`HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP Wed Apr 29 10:16:03 UTC 2026 aarch64 GNU/Linux`，
  运行身份 `uid=gid=20020105`（非 root，groups=… file_manager/log/readproc…），stdin = pipe（无控制终端）
- 原始读数全文 + 逐调用分类：见本文件 `notes.md` 附录 A（真机原始读数全文）/ 附录 B（探针源码全文 + sha256）/ 附录 C（方法学自我更正）。结论摘要：

| 调用 | 读数 | 分类 | 定性 |
|---|---|---|---|
| `open("/dev/console", O_RDWR)` | `-1 / errno=13 Permission denied` | **EACCES = 权限面** | 能力存在，非 root 不可达 |
| `open("/dev/tty1", O_RDWR)` | `-1 / errno=2 No such file or directory` | **ENOENT = 节点不存在** | 本平台**没有虚拟控制台节点** tty1…（rungetty 的传统使用前提不成立） |
| `open("/dev/tty0", O_RDWR)` | `-1 / errno=13 Permission denied` | **EACCES = 权限面** | 节点存在但非属主不可开 |
| `open("/dev/tty", O_RDWR)` | `-1 / errno=6 No such device or address` | **ENXIO**（与 Linux 一致：无控制终端时即 ENXIO） | 无偏差 |
| `tcgetattr(0)` / `ioctl(0,TCFLSH)`（fd=pipe） | `-1 / errno=25 Not a tty` | **ENOTTY = 该节点不支持** | 与 Linux 一致，无偏差 |
| `posix_openpt / grantpt / unlockpt / ptsname / open(slave)` | `3 / 0 / 0 / /dev/pts/2 / 4`，全部 **OK** | — | **pty 族完整可用**（清单 #5 主问句） |
| `tcgetattr` / `tcsetattr(TCSANOW,B9600)` / `cfsetispeed(B19200)`（pty 从端） | 全部 `0` OK；`sizeof(termios)=60`、`NCCS=32` | — | **termios 结构布局与波特率枚举与 Linux/glibc 一致，无偏差** |
| `ioctl(fd, TIOCSCTTY, 1)` — 普通进程 | `-1 / errno=1 Operation not permitted` | **EPERM = 权限面（前置条件）** | 与 Linux 一致：非会话首进程必 EPERM |
| `ioctl(fd, TIOCSCTTY, 1)` — `setsid()` 后（新会话首进程） | `setsid()`→新 sid，`ioctl` **ret=0 OK**（重复调用亦 0） | **成功** | ★**接管控制终端语义在 OHOS 可用**，rungetty 的核心机制成立 |
| `ioctl(fd, TIOCCONS)` | `-1 / errno=13 Permission denied`（两种会话态同） | **EACCES = 权限面** | 能力存在，需特权 |
| `ioctl(fd, TCFLSH, TCIOFLUSH)` / `(TCFLSH, 0)` | `-1 / errno=13 Permission denied` —— **即使在会话首进程 + 自己打开的 tty 上仍 EACCES** | **EACCES ≠ ENOTTY ≠ ENOSYS** | ★**与 Linux 有偏差**：Linux 对属主打开的 tty 返回 0。rungetty 的 `rungetty.c:305`、`:594` 两处 `ioctl(0,TCFLSH,…)` **在本平台必然失败** |
| `vhangup()` libc 包装 | 链接期 `ld.lld: error: undefined symbol: vhangup` | **符号缺失（能力缺失）** | 见 P2 |
| `syscall(SYS_vhangup)`（宏存在，nr=58） | fork 子进程被 **SIGNAL 31 (SIGSYS, Bad system call)** 杀死 | **不是 ENOSYS，是过滤器击杀** | ★对"libc 未导出"的接口**禁止按号裸调**，会当场杀进程 |

- **对本包的意义（适用边界）**：
  1. `TIOCSCTTY` 可用 ⇒ rungetty 的"接管 tty 并运行程序"主链路在 OHOS 上语义成立（init 以 root 派生时前置条件满足）。
  2. `TCFLSH` 一律 EACCES ⇒ 两处清缓冲调用静默失效；**上游未检查其返回值**（`rungetty.c:305/:594` 无返回值判定），
     故不致失败，只是行为降级为"不清输入队列"。⇒ **不得为此加 stub、不得改上游语义**，只记边界。
  3. 本平台**无 `/dev/tty1`**（ENOENT）而 `/dev/console` 需特权 ⇒ 本包在 OHOS 上的现实定位是
     "可编译、可安装、可按参数运行的 getty 实现"，真正作为 inittab getty 使用需 root + 存在相应终端节点，
     属平台使用前提而非适配缺陷。
  4. `vhangup` 缺失 ⇒ 会话首进程"吊销旧 fd"这一步在 OHOS 上不做（上游忽略返回值，语义等价降级）。

## 上游测试清点与消费者测试（R51 / R34）

- **上游 0 用例**，实证依据：①归档 8 个文件（见上），无 tests 目录/无 `.t`/无测试源；
  ②Makefile 目标全集只有 `all install rungetty clean`，无 `check`；
  ③`make -n check` → `No rule to make target 'check'`。
  ⇒ 申报口径：**上游无测试、适配后补全**（`test_package/MANIFEST.yml` 的 `upstream_tests: []` 同步记证据）。
- 消费者测试新增 **11 条断言**（`test_package/test_rungetty.py`，全部真跑安装包里的二进制）：
  T0 二进制存在可执行（L1e 反向验证挂钩）/ T1 `--help` 退出码 1 / T2 stderr 含 getopt 的
  `unrecognized option` 原文 / T3 缺 tty 操作数退出码 1 / T4 全部调用不得死于信号 /
  T5 ELF 可被加载器接受（非 126/127）/ **T6【鸿蒙特有】按探针对账：`tty1` 必须以 1 失败（本平台无该节点）** /
  T7 不存在的 tty 线路以 1 失败 / T8 `-d/-n` 短选项仍被解析 / T9 man8 落在 FHS 的 `share/man/man8/` /
  T10 application 包不得产出 `lib/`。
- 真机实测：`conan create` 的 `Testing package` 阶段 **11/11 PASS**（日志
  `reports/conan-create.log` L91–L101（全文 102 行）），`conan-verify` rc=0（G0–G4 + L2/L4/L5 全通过）。
- 未覆盖项如实记录：rungetty 的"真正跑起 getty 会话"（`chown`+`TIOCSCTTY`+`exec` 全链路）在非 root
  且无 `/dev/tty1` 的构建主机上不可达，因此 T6/T7 断言的是**与探针对账的失败语义**而非成功链路；
  没有用空壳测试假装可用。

## 依赖版本

- 无外部依赖（`requirements()` 为空；`ci/scripts/preflight_check.sh rungetty/1.2` → 无依赖需检查，rc=0）。
- 仅链接 OHOS libc（termios/ioctl/getopt/utmp/syslog 均为 libc 提供，链接期无需 `-l`）。

## 验证结果

```bash
bash ci/scripts/preflight_check.sh rungetty/1.2                 # rc=0，无依赖
python3 scripts/ohc-run.py recipe-search rungetty               # rc=0，无相似配方（语料 6173 条）→ 走模板
sh ~/tmp/uc2/gate.sh                                            # GATE_PASS（MemAvailable=13379MB，load≈20）
sh ~/tmp/uc2/build-slot.sh --kind short --mem 2500 -- \
  python3 scripts/ohc-run.py conan-verify rungetty 1.2          # rc=0（第 2 轮；第 1 轮 G2 FAIL=P6）
```

## 交付物

| 文件 | 说明 |
|------|------|
| `archives/r/rungetty/manifest.yaml` | 软件级元数据 + 版本索引 |
| `archives/r/rungetty/README.md` | 软件描述 + 探针结论摘要 |
| `archives/r/rungetty/commands.json` | R38 命令行工具声明（type=tool，versions["1.2"].ref=rungetty/1.2） |
| `1.2/conanfile.py` | 配方（R33 取 CC、x-gzip urllib 回退、配方侧安装） |
| `1.2/conandata.yml` | 官方 URL + 官方 sha256 + 补丁声明 |
| `1.2/patches/0001-libc-portability.patch` | P1 + P2 两处 libc 可移植性修改 |
| `1.2/test_package/{conanfile.py,test_rungetty.py,MANIFEST.yml}` | 11 条消费者断言 + 上游测试清点 |
| `1.2/manifest.yaml` | 版本级编译元数据（status: built，W3 通过后才写） |
| （不入库）`1.2/reports/*` | 框架生成的验证证据；当前 `.gitignore` 已整体忽略 `reports/`，故探针原始读数与源码全文以附录 A/B 形式随本文件交付 |

## 注意事项

- `.ci-result.json`、`.build-cache/`、`.conan-verified`、`.handoff.json`、`TASK_CARD.md` 等平台门禁/运行时产物**不入仓**（他包先例：`.ci-result.json` 进 PR ⇒ CI `JC5 未登记隐藏文件` blocking；本仓 `.gitignore` 第 91/96/174/254 行已覆盖，提交一律走 `git add -- <精确路径>`）。
- W3 本地 CI 模拟的 `junk_check` 在**分支无提交**时退回 `full` 模式（`git diff origin/main...HEAD` 为空 ⇒ 扫 `git ls-files` 全仓），会撞上他人归档里已入库的隐藏状态文件（实测 3 例：`archives/c/cloog/0.21.1/.build-closed`、`.staging-verified`、`archives/k/kics/2.1.20/.staging-verified`，均为 HEAD 既有内容，非本包引入）⇒ 先提交本包文件再跑 finish，使其进入 `incremental` 模式；他人归档不动。
- 本轮**未**走 `ohc-run.py build`（14 步驱动会 `conan-init` 覆盖已写配方），采用 模式 B 的
  `conan-verify` → `finish` 路线，与 SKILL §1.1 一致；`build` Step3 恒红与此无关。
- 未使用 `save_script("conanbuild")`（自引用栈溢出坑），配方不生成 env 脚本、直接从 conf 取编译器。
- 若后续要把它真正挂到 inittab 上跑，需要 root + 平台提供终端节点；那是**使用前提**，不是配方缺口。

---

## 附录 A —— 探针真机原始读数（全文未删改）

设备 `HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP Wed Apr 29 10:16:03 UTC 2026 aarch64 GNU/Linux`，
运行身份 `uid=gid=20020105`（非 root），stdin=pipe（无控制终端），
编译器 `/data/service/hnp/bin/clang`（clang 15.0.4 / `aarch64-unknown-linux-ohos`），
命令 `timeout 30 ./probe_tty_ctty`（rc=0）。

```
uid=20020105 sid=31057 pgid=31156 | fd0=pipe:[12517] isatty(0)=0
ioctl(0,TCFLSH,TCIOFLUSH)      ret=-1     errno=25  Not a tty                ENOTTY:unsupported-on-node
tcgetattr(0)                   ret=-1     errno=25  Not a tty                ENOTTY:unsupported-on-node
open(/dev/console)             ret=-1     errno=13  Permission denied        EPERM/EACCES:permission
open(/dev/tty1)                ret=-1     errno=2   No such file or directory ENOENT:node-missing
open(/dev/tty0)                ret=-1     errno=13  Permission denied        EPERM/EACCES:permission
open(/dev/tty)                 ret=-1     errno=6   No such device or address ENXIO:no-device
--- console/tty attempts (no session change): fd=-1 ttyname=? sid=31057 ---
posix_openpt(O_RDWR|O_NOCTTY)  ret=3      errno=0   success                  OK
grantpt                        ret=0      errno=0   success                  OK
unlockpt                       ret=0      errno=0   success                  OK
ptsname=/dev/pts/2
open(pts slave)                ret=4      errno=0   success                  OK
--- pty slave, parent session: fd=4 ttyname=/dev/pts/2 sid=31057 ---
tcgetattr                      ret=0      errno=0   success                  OK
    sizeof(termios)=60 NCCS=32 c_iflag=02400 c_oflag=05 c_cflag=0277
tcsetattr(TCSANOW,B9600)       ret=0      errno=0   success                  OK
cfsetispeed(B19200)            ret=0      errno=0   success                  OK
ioctl(TIOCSCTTY,1)             ret=-1     errno=1   Operation not permitted  EPERM/EACCES:permission
ioctl(TIOCCONS)                ret=-1     errno=13  Permission denied        EPERM/EACCES:permission
ioctl(TCFLSH,TCIOFLUSH)        ret=-1     errno=13  Permission denied        EPERM/EACCES:permission
ioctl(TCFLSH,0)                ret=-1     errno=13  Permission denied        EPERM/EACCES:permission
  (SYS_vhangup macro: defined, nr=58)
  child TERMINATED BY SIGNAL 31 (Bad system call) -> syscall refused by the platform filter, not by ENOSYS
  setsid()                     ret=31173  errno=0   success                  OK
--- pty slave, new session leader: fd=4 ttyname=/dev/pts/2 sid=31173 ---
tcgetattr                      ret=0      errno=0   success                  OK
    sizeof(termios)=60 NCCS=32 c_iflag=02400 c_oflag=05 c_cflag=0275
tcsetattr(TCSANOW,B9600)       ret=0      errno=0   success                  OK
cfsetispeed(B19200)            ret=0      errno=0   success                  OK
ioctl(TIOCSCTTY,1)             ret=0      errno=0   success                  OK
ioctl(TIOCCONS)                ret=-1     errno=13  Permission denied        EPERM/EACCES:permission
ioctl(TCFLSH,TCIOFLUSH)        ret=-1     errno=13  Permission denied        EPERM/EACCES:permission
ioctl(TCFLSH,0)                ret=-1     errno=13  Permission denied        EPERM/EACCES:permission
  (SYS_vhangup macro: defined, nr=58)
  child TERMINATED BY SIGNAL 31 (Bad system call) -> syscall refused by the platform filter, not by ENOSYS
  ioctl(s,TIOCSCTTY,1) again   ret=0      errno=0   success                  OK
```

（同一轮链接期证据：`printf '#include <unistd.h>
int main(void){return vhangup();}' | clang -x c - -o t`
→ `ld.lld: error: undefined symbol: vhangup`；加 `-D_GNU_SOURCE` 同结果。）

## 附录 B —— 探针源码全文（139 行，sha256 `b314a554239d8de32933ce96263755b49f7f18d21bb92b619812291306a0b3f9`）

```c
/* OHOS 行为探针 #5（pty/termios 家族）：console/TTY 语义 —— ctty/vhangup/TCFLSH/TIOCCONS
 * 独立程序，不引任何三方库；用与 rungetty 配方同一套 OHOS clang 编译、A 机真机运行。
 * 每行输出：调用 / 返回值 / errno / strerror 原文 / 定性分类
 *   （ENOSYS=能力缺失、ENOTTY=该节点不支持、EPERM|EACCES=权限面、ENOENT=节点不存在、
 *     ENXIO=无设备、OK=成功）。分类不合并。
 */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/wait.h>
#include <termios.h>
#include <unistd.h>
#include <sys/syscall.h>

#define R(w, e)                                                               \
  do                                                                          \
    {                                                                         \
      long v_ = (long) (e);                                                   \
      int s_ = errno;                                                         \
      printf ("%-30s ret=%-6ld errno=%-3d %-24s %s\n", w, v_, v_ < 0 ? s_ : 0,\
              v_ < 0 ? strerror (s_) : "success",                             \
              v_ >= 0 ? "OK"                                                  \
              : s_ == ENOSYS ? "ENOSYS:capability-missing"                    \
              : s_ == ENOTTY ? "ENOTTY:unsupported-on-node"                   \
              : (s_ == EPERM || s_ == EACCES) ? "EPERM/EACCES:permission"     \
              : s_ == ENOENT ? "ENOENT:node-missing"                          \
              : s_ == ENXIO ? "ENXIO:no-device" : "other-errno");             \
      errno = 0;                                                              \
      fflush (stdout);                                                        \
    }                                                                         \
  while (0)

static void
raw_vhangup (void)
/* vhangup(2) has no libc wrapper in OHOS libc (link error: undefined symbol),
 * so the kernel entry point is attempted by number.  It runs in a forked child
 * because an unwhitelisted syscall is killed by the platform filter (SIGSYS)
 * instead of returning ENOSYS. */
{
  int nr =
#ifdef SYS_vhangup
      SYS_vhangup
#else
      446                           /* aarch64 generic table */
#endif
      ;
  pid_t p = fork ();
  int st;
  printf ("  (SYS_vhangup macro: %s, nr=%d)\n",
#ifdef SYS_vhangup
          "defined"
#else
          "absent"
#endif
          , nr);
  if (p == 0)
    {
      long v = syscall (nr);
      int e = errno;
      printf ("  child: syscall(%d=vhangup) ret=%ld errno=%-3d %s\n", nr, v,
              v < 0 ? e : 0, v < 0 ? strerror (e) : "success");
      fflush (stdout);
      _exit (0);
    }
  waitpid (p, &st, 0);
  if (WIFSIGNALED (st))
    printf ("  child TERMINATED BY SIGNAL %d (%s) -> syscall refused by the "
            "platform filter, not by ENOSYS\n", WTERMSIG (st),
            strsignal (WTERMSIG (st)));
  else
    printf ("  child exited normally, status=%d\n", WEXITSTATUS (st));
  fflush (stdout);
}

static void
seq (const char *tag, int fd)
{
  struct termios ts;
  printf ("--- %s: fd=%d ttyname=%s sid=%d ---\n", tag, fd,
          fd >= 0 && ttyname (fd) ? ttyname (fd) : "?", (int) getsid (0));
  if (fd < 0)
    return;
  R ("tcgetattr", tcgetattr (fd, &ts));
  printf ("    sizeof(termios)=%zu NCCS=%d c_iflag=%#o c_oflag=%#o c_cflag=%#o\n",
          sizeof (struct termios), NCCS, ts.c_iflag, ts.c_oflag, ts.c_cflag);
  ts.c_cflag = (ts.c_cflag & ~CBAUD) | B9600;
  R ("tcsetattr(TCSANOW,B9600)", tcsetattr (fd, TCSANOW, &ts));
  R ("cfsetispeed(B19200)", cfsetispeed (&ts, B19200));
  R ("ioctl(TIOCSCTTY,1)", ioctl (fd, TIOCSCTTY, (void *) 1));
  R ("ioctl(TIOCCONS)", ioctl (fd, TIOCCONS));
  R ("ioctl(TCFLSH,TCIOFLUSH)", ioctl (fd, TCFLSH, TCIOFLUSH));
  R ("ioctl(TCFLSH,0)", ioctl (fd, TCFLSH, 0));
  raw_vhangup ();
  fflush (stdout);
}

int
main (void)
{
  int m = -1, s = -1, pid, st;
  char link[128], *sp;
  struct termios ts;

  printf ("uid=%d sid=%d pgid=%d | fd0=%s isatty(0)=%d\n", (int) getuid (),
          (int) getsid (0), (int) getpgid (0),
          readlink ("/proc/self/fd/0", link, sizeof link - 1) > 0 ? link : "?",
          isatty (0));
  R ("ioctl(0,TCFLSH,TCIOFLUSH)", ioctl (0, TCFLSH, TCIOFLUSH));
  R ("tcgetattr(0)", tcgetattr (0, &ts));
  R ("open(/dev/console)", m = open ("/dev/console", O_RDWR));
  R ("open(/dev/tty1)", s = open ("/dev/tty1", O_RDWR));
  R ("open(/dev/tty0)", open ("/dev/tty0", O_RDWR));
  R ("open(/dev/tty)", open ("/dev/tty", O_RDWR));
  seq ("console/tty attempts (no session change)", m >= 0 ? m : s);
  R ("posix_openpt(O_RDWR|O_NOCTTY)", m = posix_openpt (O_RDWR | O_NOCTTY));
  if (m >= 0)
    {
      R ("grantpt", grantpt (m));
      R ("unlockpt", unlockpt (m));
      sp = ptsname (m);
      printf ("ptsname=%s\n", sp ? sp : "(null)");
      R ("open(pts slave)", s = sp ? open (sp, O_RDWR | O_NOCTTY) : -1);
      seq ("pty slave, parent session", s);
      pid = fork ();
      if (pid == 0)
        {
          R ("  setsid()", (long) setsid ());
          seq ("pty slave, new session leader", s);
          R ("  ioctl(s,TIOCSCTTY,1) again", ioctl (s, TIOCSCTTY, (void *) 1));
          _exit (0);
        }
      if (pid > 0)
        waitpid (pid, &st, 0);
    }
  return 0;
}
```

## 附录 C —— 探针方法学自我更正（留痕，防后人复用错结论）

- 第一版探针把 `#include <sys/syscall.h>` 写在 `#ifdef SYS_vhangup` 里 ⇒ 宏永不可见，
  于是打印"SYS_vhangup 宏在头文件中不存在"，且紧接的按号 `syscall(446)` 把进程打死
  （表现为 `timeout: the monitored command dumped core / Signal 31`）。
  **该读数是探针自身的 include 守卫 bug，不是平台事实。**
- 修正后事实：`SYS_vhangup` **存在**（nr=58），但按号调用被平台 syscall 过滤器以 **SIGSYS 击杀进程**（不是 ENOSYS）。
- 教训（可复用）：**可能击杀进程的 syscall 探测必须放 fork 子进程**，否则一次崩溃丢掉后续全部读数。
---

**编译结束**: 2026-09-25 19:50
**最终状态**: built
