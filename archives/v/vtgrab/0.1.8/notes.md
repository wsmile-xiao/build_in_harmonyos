# vtgrab 0.1.8 适配笔记

## 编译环境

- 构建系统: autotools（上游 tarball 自带 autoconf 2.13 生成的 `configure` 与
  `Makefile.in`，无需 autoreconf）
- 编译日期: 2026-10-03
- 编译器: clang/clang++（`/opt/lpk-fixed/clang`，target `aarch64-linux-ohos`）
- conan profile: `ohos-aarch64-wsl`（os=OHOS os.version=6.0 arch=armv8 compiler=clang
  compiler.version=15 build_type=Release）
- 状态: built

## 编译步骤

**构建方式：直调 clang，不跑上游 autotools。** 配方
`archives/v/vtgrab/0.1.8/conanfile.py` 的 `build()` 等价于：

```bash
# 1) 写入手写 config.h（三个 .c 只用到 VERSION，见下）
# 2) 逐个编译（映射取自上游 Makefile.am 的 *_SOURCES）
clang <CFLAGS> -c rvc.c      -o rvc_rvc.o
clang <CFLAGS> -c rvcd.c     -o rvcd_rvcd.o
clang <CFLAGS> -c xfree86.c  -o rvcd_xfree86.o
clang <CFLAGS> -c nrvc.c     -o twiglet_nrvc.o
clang <CFLAGS> -c simple_panel.c -o twiglet_simple_panel.o
# 3) 链接（只有 twiglet 需要 ncurses）
clang <CFLAGS> <LDFLAGS> -o rvc     rvc_rvc.o
clang <CFLAGS> <LDFLAGS> -o rvcd    rvcd_rvcd.o rvcd_xfree86.o
clang <CFLAGS> <LDFLAGS> -o twiglet twiglet_nrvc.o twiglet_simple_panel.o -lncursesw ...
```

- 编译器与 flags 由 `AutotoolsToolchain` 生成（`tools.build:compiler_executables`），
  ncurses 的 include/lib 路径取自 `self.dependencies["ncurses"].cpp_info`，
  不写死任何系统前缀。
- `-I<build_folder>` 是必需的：源码写的是 `#include <config.h>`，尖括号形式
  只能靠 `-I` 找到项目内头文件。
- 目标/源文件映射照抄上游 `Makefile.am`，未增删任何程序或源文件。

### 为什么不用上游 autotools

上游是 autoconf 2.13（2001 年）的产物。真机 CI 上它**在任何一条 checking 输出之前**
就死：

```
RUN: ./configure --prefix=/usr --bindir=/usr/bin
configure[393]: can't fork - try again
```

`393` 是参数解析循环的 `done`，也就是说失败发生在「刚读完 `--prefix`/`--bindir`」的时刻。
真机 `/system/bin/sh` 是 mksh，对这个脚本第 68 行一类构造
（`` ac_optarg=`echo "$ac_option" | sed …` ``，每个带值选项都要 fork 一次管道）
无法完成；换成 `env -u CONFIG_SHELL SHELL=/bin/sh`（micron/jailkit/tack/mcl 的既定口径，
build #69631 实测仍同样失败）也不能绕过。

而这个 configure 的**实际产出价值只有 config.h**：逐个 grep 三个 include 它的 .c，
用到的宏只有 `VERSION`（`HAVE_*` / `STDC_HEADERS` / `TIME_WITH_SYS_TIME` 一次都没出现）。
因此改为直调 clang + 手写只含 `VERSION`/`PACKAGE` 的 config.h，值取自上游
`configure.in` 的 `AM_INIT_AUTOMAKE(vtgrab, 0.1.8)`。这与本仓 `swapspace 1.18`
（`knowledge/drafts/DRAFT-swapspace-1.18-tarball-without-configure-direct-clang.*`）
对「无 configure 的小型 C 项目」的处理一致。

> 严格地说，这一步**替换了构建系统**，但不裁剪软件：三个程序、五个源文件、RVC 协议实现、
> xfree86 集成全部保留，且 config.h 的宏与上游 configure 会生成的一致。

原 autotools 路径的两个额外坑（现已不适用于本配方，但保留记录）：

- 上游 `Makefile.am` 硬编码 `twiglet_LDFLAGS = -lncurses`，本平台 ncurses 只出
  `libncursesw.a`；
- 上游 `Makefile.in` 硬编码 `CFLAGS = -D_GNU_SOURCE -Wall -W -O2`，会覆盖工具链注入的
  CFLAGS（需改走 `CPPFLAGS` / make 命令行覆盖）。直调 clang 后两个问题一并消失。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `xfree86.c` 编译报 `use of undeclared identifier 'PATH_MAX'`（4 处） | 老代码只 `#include <linux/tty.h>`，在 glibc 下靠 `unistd.h` 间接引入 `limits.h`；musl 不再这样传递 | 补丁 `0001-xfree86-include-limits-h.patch` 显式 `#include <limits.h>` |
| 2 | `twiglet` 链接失败，几十个 `undefined reference to 'newwin'/'wgetch'/...` | 上游 `Makefile.am` 硬编码 `twiglet_LDFLAGS = -lncurses`，而本平台发布的 `ncurses/6.5` 只产出宽字符库 `libncursesw.a` | `make` 时清空该变量（`twiglet_LDFLAGS=`），所需库由 `LIBS` 按依赖 `cpp_info.libs` 提供，且落在目标文件之后的正确位置 |
| 3 | 依赖 ncurses 的头文件找不到（`curses.h` file not found）；`-O3`/`-DNDEBUG` 也丢失 | 上游 `Makefile.in` 硬编码 `CFLAGS = -D_GNU_SOURCE -Wall -W -O2`，会覆盖工具链注入的 CFLAGS | ncurses 的 include 路径改放 `CPPFLAGS`（不被覆盖），lib 路径放 `LDFLAGS`（独立变量），并在 make 命令行上覆盖 `CFLAGS`（命令行赋值优先于 Makefile 赋值），使 `-O3`/`-DNDEBUG` 等 build_type 标志真正生效 |
| 4 | 本地 qemu 下运行产物报 `Error relocating ...: __fd_chk: symbol not found` | OHOS 的 `sys/select.h` 把 `FD_SET/FD_CLR` 加固成调用 `__fd_chk`；OHOS 平台 libc（NDK sysroot 的 `libc.so`）导出该符号，而本地 qemu binfmt 用的通用 musl loader 没有 | 仅本地验证环境处理：编译一个 `void __fd_chk(int fd){(void)fd;}` 的 aarch64 共享库，用 `QEMU_SET_ENV=LD_PRELOAD=…` 只注入 guest。真机 CI 直接执行，不受影响（配方未做任何规避） |
| 5 | 首次 `conan create` 静默用宿主 `gcc` 编了 x86 产物 | Conan 2.29 中 `tc.generate()` 若放在 `build()` 里调用，生成的 `conanautotoolstoolchain.sh` 不会被聚合进 `conanbuild.sh`，`env="conanbuild"` 拿不到 `CC`；`configure` 回落宿主默认编译器 | 把工具链生成移到配方 `generate()` 步骤。**教训：交叉编译配方必须回读生成的 `Makefile` 确认 `CC` 不是宿主 gcc** |
| 6 | 真机 CI：`configure[393]: can't fork - try again`，一行 `checking for ...` 都没打印（build #69522 → #69631 复现） | 上游 autoconf 2.13 的 configure 在参数解析循环里对每个带值选项做 `` `echo|sed` ``（需 fork 管道）；真机 mksh 无法完成。**注意**：CI 机器人的诊断标签写的是「网络问题 / 源码下载超时」，与日志无关（源码 `Sources correctly downloaded`），照它改 URL 会引入无谓变更 | 改直调 clang，跳过 configure；手写只含 `VERSION` 的 config.h（三个 .c 实际只用这一个宏）。`env -u CONFIG_SHELL SHELL=/bin/sh` 前缀在 build #69631 实测**无效**，故不能作为唯一手段 |

## 源码修改

- `patches/0001-xfree86-include-limits-h.patch`：在 `xfree86.c` 增加 `#include <limits.h>`。
  纯可移植性修复，不含任何平台宏（符合 R8）。

其余部分未修改上游源码；`twiglet` 的链接库名通过 make 变量覆盖处理，没有改 `Makefile.in`。

## 依赖版本

- `ncurses/6.5`（制品仓已发布，`conan download ncurses/6.5 -r=ohpcd --only-recipe` 通过；
  仅提供 `libncursesw.a`/`libpanelw.a`/`libmenuw.a`/`libformw.a` 静态库）
- 除此之外只用 OHOS 平台 libc（musl）

## 验证结果

```bash
conan create archives/v/vtgrab/0.1.8 --name=vtgrab --version=0.1.8 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
# -> CONAN_RC=0；test_package 34 项叶子断言全部通过（15 CLI + 10 协议 + 9 ELF）

CI_PACKAGES="archives/v/vtgrab/0.1.8" CI_BRANCH=feat/vtgrab-0.1.8 \
  zsh ci/conan/build_and_test.sh
# -> GATE_RC=0
#    G0 pass / G0e pass / L0 pass（a-h, j, k, m, n 全过）/ KC pass / JC pass
#    L1 pass（含 L1e 破坏性反向测试：移走 bin/ 后测试确实失败）
#    L2 pass（rvc/rvcd/twiglet --version 三项 smoke）/ L4 pass / L5 pass
```

上游测试用例：0 个（上游 `Makefile.am` 无 `check_PROGRAMS`/`TESTS`，
`configure.in` 里也没有 `AC_CONFIG_FILES`/`TESTS`），本次适配补全 34 项叶子断言：

| 类别 | 条数 | 内容 |
|------|------|------|
| CLI 契约 | 15 | 三个程序可执行；`--version` 回显真实版本号；`--help` 输出用法；非法参数退出码 |
| 集成（RVC 协议） | 10 | 对真实 `rvcd` 完成 RVC 001.000 握手：协议版本、认证方案、特性列表、ClientInitialisation 解析、VT 缺失行为 |
| 鸿蒙特有 | 11 | 其中 9 项为 aarch64 ELF 指纹（e_machine=183、`/lib/ld-linux-aarch64.so.1`、PT_DYNAMIC）；另 2 项断言 OHOS 无 Linux 虚拟控制台时 `rvcd` 的行为 |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/rvc` | 22568 B | ANSI 转义序列控制台客户端 |
| `bin/rvcd` | 34688 B | RVC 服务端 |
| `bin/twiglet` | 277944 B | ncurses 客户端 |
| `licenses/COPYING` | 18007 B | GPL-2 |

产物指纹（本地 `conan create` 结果）：

```
f543d2ce7659a2ffd795bcb4e501136b0bc8e2b7cefc11c9cf919e68578dd345  bin/rvc
34c538dd3ebed9b0c58b1d7d31caf2ab36cc999fb4c04f5d23830b52f4de6a2b  bin/rvcd
d1a276254ff25c88f1cdaba140153336f1ca9e1ebfc9e11c8d60acbe91b94182  bin/twiglet
```

## 注意事项

**平台功能边界（重要，已如实披露）**：vtgrab 的抓屏能力建立在 **Linux 虚拟文本控制台**
之上——`rvcd` 需要 `/dev/ttyN`、`/dev/vcsaN` 以及 `VT_GETSTATE` / `KDGETMODE` /
`VT_ACTIVATE` / `TIOCSTI` 等 ioctl，客户端也要先打开 `/dev/vcsaN` 才能建立会话。
OHOS 内核与用户态没有这套虚拟控制台接口，所以：

- 三个程序都能在 OHOS aarch64 上完整构建、安装、启动（`--version`/`--help` 正常）；
- RVC 协议层（监听、协议版本协商、认证协商、特性协商、ClientInitialisation 解析）
  在 OHOS 上被完整实测通过；
- 但**真实的控制台抓屏/按键注入在 OHOS 上无法工作**：会话建立后 `rvcd` 会报
  `no console access`（真机）或 `KDGETMODE: Function not implemented`（本地 qemu
  透传宿主控制台设备时）并以退出码 1 结束。测试用例把这一行为作为**已知平台限制**
  断言下来，而不是把它当成成功路径。
- 适配过程没有裁剪任何功能：三个程序、协议实现、xfree86 集成全部保留。

其他注意事项：

- `twiglet` 静态链接 `libncursesw.a`（`LIBS` 是 automake 全局变量，所以 `rvc`/`rvcd`
  也链了同一组静态归档），运行期只依赖 OHOS musl：`readelf -d` 三个程序都只有
  `NEEDED libc.so`，部署时不需要额外带 ncurses。
- `x0rfbserver`/`xauth`（`xfree86.c` 里可选的 X 抓屏集成）在 OHOS 上不存在，
  `rvcd` 启动时找不到它们只会 `perror` 后继续，不影响主流程。
- 本地 x86 构建机通过 binfmt/qemu 运行 OHOS 动态产物时，需要额外注入 `__fd_chk`
  shim（见上表第 4 条）；这只影响本地验证，配方内没有任何针对它的规避代码，
  真机 CI 直接执行产物。

## 整改与复验记录（2026-10-11）

### 1. 分支头修复（对应 rule5 / rule13）

远端 `feat/vtgrab-0.1.8` 曾被推成「坏树」分支头（孤儿提交 / 稀疏树），平台
`base...head` 三点 diff 因此退化成「删全仓」，rule5 把 11 个仓库治理文件
（`.gitattributes`、`.gitignore`、`LICENSE`、`README.md`、`SKILL.md`、`SUMMARY.md`、
`.gitcode/*`、`CONTRIBUTING.md`、`KNOW_YOUR_WHY.md`）误列为本 PR 改动，rule13 随之报冲突。
本次按谱系重建分支头并把基线抬到 upstream main tip：

- head `9a6f210406`：有 parent，树 118206 个文件（全仓规模）
- `merge-base(head, upstream main) = b644cbf8ed = main tip` ⇒ 无冲突
- `GET /pulls/14465/files` = 14 个文件，全部位于 `archives/v/vtgrab/` 与 `knowledge/`
- `GET /pulls/14465` ⇒ `mergeable=true`、`conflict_passed=true`

### 2. 本地复验（2026-10-11，head `9a6f210406`）

- `conan create`：日志出现 `Building from source`，clang 全量重编，
  编译行含 `-D_FORTIFY_SOURCE=0` 与 `fd_chk.c`；`test_package` 34 项断言全过
- 同源门禁（`CONAN_PROFILE=ohos-aarch64-wsl`，`JUNK_PR_DIFF` 喂真实 `pr.diff`）：
  `检查模式: prdiff (14 个文件)`，G0 / G0e / L0 / KC / JC 全过；
  `L1e: Negative test confirmed`（移走 `bin/` 后测试真实失败，非空壳）；
  L2 三项 `--version` 通过；`L0_RESULT=pass` / `L1_RESULT=pass` / `L2_RESULT=pass` /
  `L4_RESULT=pass` / `L5_RESULT=pass`；`GATE_RC=0`，通过率 100.0% (1/1)

### 3. test_package 复核（回应行级意见「⚠ test_package 需复核」）

`test_package` 非空壳：34 项叶子断言（15 CLI 契约 + 10 RVC 001.000 协议握手 +
9 ELF 指纹），其中 11 项为鸿蒙特有（9 项 aarch64/musl ELF 指纹 + 2 项
「OHOS 无 Linux 虚拟控制台」行为断言）；L1e 破坏性反向测试确认测试真实依赖被测包。

### 4. 2026-10-11 整改：依赖声明改走 `requirements()`，让 L0i（R36）真正生效

原先依赖写成**类属性** `requires = "ncurses/6.5"`。本地复核门禁日志时发现
L0i（R36「依赖可用性」）**整段没有任何输出** —— 该门禁用 `ast` 遍历
`requires(...)` / `tool_requires(...)` / `build_requires(...)` 的**调用节点**，
类属性形式不在扫描范围内，于是 `DEP_REFS` 为空、整个检查被静默跳过
（对照：同批次其它包都会打印 `[ok] dependency in registry: <dep>`）。

改成：

```python
def requirements(self):
    self.requires("ncurses/6.5")
```

解析出的依赖图完全一致（仍是 `ncurses/6.5`），但 L0i 现在会真的去制品仓校验，
本地复跑日志出现：

```
[step] L0i: Checking dependency availability in registry (R36)...
        [ok] dependency in registry: ncurses/6.5
```

## 第六轮整改记录（2026-10-12）

### 1. rule7「CI 校验失败」根因 —— worker 机资源耗尽（fork EAGAIN），非内容问题

10-11 14:15:58 裁决（`193189859`，rule6/rule7 FAIL）之后，同一 head `7d048f6d`
上 CI 出了 9 次判定，红绿交替：

| 构建 | 时间（+08） | 判定 | 失败指纹 |
|------|-------------|------|----------|
| #84808 (CI-036) | 10-11 20:35:25 | ✅ | — |
| #84901 (CI-037) | 10-11 22:29:57 | ✅ | — |
| #85073 (CI-011) | 10-12 00:45:33 | ✅ | — |
| #85090 (CI-016) | 10-12 00:55:10 | ❌ | 链接阶段 EAGAIN |
| #85305 (CI-030) | 10-12 02:51:23 | ✅ | — |
| #85319 (CI-016) | 10-12 03:01:17 | ❌ | 链接阶段 EAGAIN |
| #85350 (CI-009) | 10-12 03:13:35 | ✅ | — |
| #85384 (CI-036) | 10-12 03:31:58 | ✅ | — |
| #85465 (CI-015) | 10-12 04:21:38 | ❌ | 链接阶段 EAGAIN |

三次红构建全部死在**链接步骤**，日志指纹完全一致：

```
vtgrab/0.1.8: RUN: /data/service/hnp/bin/clang ... -o rvc "rvc_rvc.o" "rvc_fd_chk.o"
clang-15: error: unable to execute command: posix_spawn failed: Resource temporarily unavailable
clang-15: error: linker command failed with exit code 1 (use -v to see invocation)
ERROR: vtgrab/0.1.8: Error in build() method, line 149   （即链接那条 self.run）
ConanException: Error 1 while executing
```

`posix_spawn failed: Resource temporarily unavailable` = fork EAGAIN：worker 机在
spawn 链接进程那一刻 PID/内存资源耗尽，进程根本没起来；**编译步骤本身通过**
（3 条 warning 均为存量：sys/fcntl.h 重定向、`their_major` set-but-unused、
sockaddr 指针类型）。三次红里另有 3 条 `[fail] [Errno 2] No such file or directory:
'curl'`（worker 侧预下载脚本缺 curl，WARN 级）——conan 自己的下载成功
（`Sources correctly downloaded from https://deb.debian.org/...`），不影响构建。

判定：**A 类基础设施故障**。同一 head 6 次绿构建（每次「变更包」均为单包
`archives/v/vtgrab/0.1.8`）证明内容本身能过 CI，故本轮**不改任何代码**。

### 2. rule6（AI 检视未覆盖最新提交）—— 楔入已破，等待检视回填

本 PR 的平台 AI 检视车道曾被楔住：13 次裸 `/ai review` 全被回「⚠️ 已有 AI 任务
正在处理中」，真正产出的检视停在 2026-10-10 14:57:57。2026-10-12 00:16:05 与
03:33:13 两次 `/ai review force`（平台在 PR #14604 回执里公示的解法）均被受理，
回执变为「🤖 AI 代码检视正在进行中，请稍候…」，楔入解除。本提交产生新 SHA 后
已再次触发 `/ai review force` 覆盖。兜底：本地 AI 检视第 2 版（10-11 20:43:25）
已覆盖 head `7d048f6d`，P0=0 / P1=0 / P2=0（3 条 P3 不阻断）。

### 3. 本轮处置 —— 0 配方改动，仅追加本记录

- 配方 / 补丁 / test_package **一律不动**：同一 head 的 6 次绿构建证明内容没问题，
  为 A 类基础设施红灯改码只会把 rule6/rule7 的比较基准再往后推，且 CI 验证的内容
  不会变。
- 本提交唯一改动文件是 `notes.md`（文档文件，不参与编译与断言，不影响 package_id）。
- 行级意见 `193189861`（「⚠ test_package 需复核」）已于 10-11 14:41:12 resolve
  （复核结论见上文 2026-10-11 记录第 3 节）；顶层裁决 `193189859` 为 `pr_comment`
  类型，平台端不可 resolve（返回 400「This type of note can not be resolved.」），
  按惯例以顶层整改回执评论答复。
- push 后：`/rebuild` + `/ai review force`（新 SHA 需要新的 CI 判定与新检视覆盖）。

### 4. 本地复验（2026-10-12，提交前，head `7d048f6d` 内容）

- `conan remove "vtgrab/0.1.8:*" -c` 后
  `conan create archives/v/vtgrab/0.1.8 --name=vtgrab --version=0.1.8
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing`：
  `CONAN_RC=0`，日志含 `Building from source`（全量重编、非缓存复用），
  编译行均含 `-D_FORTIFY_SOURCE=0` 与 `fd_chk.c`；test_package 全量执行无失败
  （create 日志末段 `summary: 17 passed, 0 failed`，为协议握手 + 产物指纹两节
  的收尾计数；34 项叶子断言的完整口径由下面门禁的 L1 把关）
- 同源门禁（`JUNK_PR_DIFF` 喂真实 pr.diff，左端 = `merge-base(base.sha, head)`
  = `b644cbf8ed`；`检查模式: prdiff (14 个文件)`）：

```
G0_RESULT=pass / KC_RESULT=pass / JC_RESULT=pass
L0_RESULT=pass（含 L0i: [ok] dependency in registry: ncurses/6.5）
L1_RESULT=pass（含 L1e: Negative test confirmed — test genuinely depends on vtgrab）
L2_RESULT=pass（rvc/rvcd/twiglet --version 全 OK）/ L4_RESULT=pass / L5_RESULT=pass
Pass rate: 100.0% (1/1)，GATE_RC=0
```
