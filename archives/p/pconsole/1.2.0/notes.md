# pconsole 1.2.0 适配笔记

## 编译环境
- 构建系统: autotools（**autoconf 2.13 世代**的手写 `configure` + 手写 `Makefile.in`，
  无 automake、无 `config.guess`/`config.sub`；发行包自带 `configure`，CI 无需 autoreconf）
- 编译日期: 2026-09-30
- 编译器: clang 15（OHOS aarch64 交叉工具链，`--target=aarch64-linux-ohos` + OHOS musl sysroot）
- 目标: `ohos-aarch64`（本机 `conan create` 用 profile `ohos-aarch64-wsl`，
  与 `ci/conan/profiles/ohos-aarch64` 同源，仅工具链路径指向本机 OHOS SDK）
- 状态: built

## 软件是什么

pconsole = parallel console，2001 年 Walter de Jong 写的集群管理工具：
一个"主控终端" + N 个"目标终端"，主控端敲的每一个按键都被 `ioctl(TIOCSTI)`
注入到所有已 attach 的 tty 的输入队列里，从而一处输入、处处执行。
交付物是 `bin/pconsole`（C 程序）+ `bin/pconsole.sh`（开窗并 attach 的驱动脚本）+
`bin/ssh.sh`（ssh 包装，因 ssh 的 tty 语义需要它）。

## 编译步骤

1. `conan create`（AutotoolsToolchain；`--prefix` 指向 conan 包目录）
2. 配置期无需 `--host` / `--build`
3. **树内构建**（in-tree）：configure 与 make 都在 `source_folder` 内执行
4. 安装：`make install`（上游 install 目标**忽略 DESTDIR**，直接写绝对 `$(bindir)`）
5. 额外 `copy(GPL → licenses/)`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | **`pconsole` 一启动就被内核杀死（鸿蒙 P0）** | `main()` 无条件 `seteuid(getuid())` 丢弃 root 权限；`put_conn()` 每次注入按键前后各一次 `seteuid(0)` / `seteuid(getuid())`。鸿蒙对应用/沙箱进程用白名单式 seccomp，特权 id syscall 不在允许列表，进程被**不可捕获**的 SIGSYS 打死（exit 159，E051），连错误分支都走不到 | `patches/0001-pconsole.c-seteuid-noop-guard.patch`：调用前先用 POSIX 判空操作——`geteuid() != getuid() && seteuid(...)`。euid==uid 时该调用按定义不改变任何 uid，跳过它是严格的空操作消除；真 setuid-root 二进制仍走原路径并原样报错。**纯 POSIX 写法、无 `__OHOS__` 平台宏**（R8/PF5），对非鸿蒙平台完全透明 |
| 2 | 树外（VPATH）构建必然失败 | 2001 年版 `Makefile.in` 用 `.c.o:` 后缀规则 + `-I$(INCLUDE) -I.`，路径相对**构建目录**；autotools 生成的 Makefile 变量（`srcdir`）一个都没有。`#include "config.h"` 也只在 build 目录 | 不打补丁，直接 `with chdir(self, self.source_folder)` 做树内构建。`config.h` 与 `include/` 都在源码树内，`.depend` 由 Makefile 自带的 `depend dep .depend:` 规则在 `include .depend` 触发时自动生成 |
| 3 | `make install` 有把文件装到真实 `/bin` 的风险 | 上游 install 目标完全无视 `DESTDIR`（conan 的 `Autotools.install()` 会传 `DESTDIR=<包目录>`，此处被丢弃），只写绝对 `$(bindir)`；而 `AutotoolsToolchain` 的默认 `prefix` 是 `"/"` | 显式 `AutotoolsToolchain(self, prefix=self.package_folder)`。`$(bindir)` 变成 `<包目录>/bin`，`make install` 原地落盘；副产品是生成的 `pconsole.sh` 里 `@prefix@`/`@bindir@` 被替换成**最终的包内路径**（可重定位），test.sh 对此有断言 |
| 4 | 不传 `--build` 是否会踩 config.guess | autoconf **2.13** 根本没有 config.guess/config.sub，也不做平台猜测（这是 E007 的老基线场景，与 2.69 基线相反） | 实测确认不需要。且 2.13 会把多余参数误判为 host 三元组（`DRAFT-sntop-1.4.3-autoconf213-*`），多传 `--build` 反而有害 |
| 5 | `configure.in` 覆盖 CFLAGS | `configure.in` 末尾无条件 `CFLAGS="$CCOPTS"`（GCC 分支 `-O2 -Wall -Wstrict-prototypes -fomit-frame-pointer`），conan/toolchain 给的 CFLAGS 被静默丢弃 | 不修。本包 `--target`/sysroot 都在 `CC` 里（工具链驱动），不在 CFLAGS，丢弃不影响正确性；改动会偏离上游配置语义（R8）。`DRAFT-autotools-configure-ac-cflags-clobber-toolchain-flags` 已有该模式条目，不重复申报 |
| 6 | `<sys/termios.h>` 编译告警 | pconsole.c 用的是 POSIX 老写法 `#include <sys/termios.h>`，OHOS sysroot 里该路径是转发头，会 `#warning redirecting incorrect #include` | 上游代码风格问题，1 条告警，不影响功能。**未**改（termios 本身是 POSIX 标准接口，不存在 E567 那种 legacy `TCGETA` 宏缺失问题——已核对 terminal.c 只用 tcgetattr/tcsetattr） |
| 7 | `pconsole.sh <host>` 绝不能在自动化测试里调用 | 无控制终端时 `get_tty()` 的 `while [ -z "$TTY" ]` 永不退出（`tty` 失败 → `THIS_TTY` 空 → 条件恒假），子 shell 无限自旋 | test.sh 只在**无参数**下调用（打印 usage 后 `exit 1`）。带参数路径不进自动化测试，已在 test.sh 注释与知识草稿里记为禁止做法 |

## 上游测试清点（R51 三步法）

**审计对象**：`pconsole-1.2.0.tar.gz`（GitHub tag `v1.2.0`，commit
`1a00ed5b2c8c9b18f4ad7799c0191c6ad8e56fe6`），sha256
`31f2adf371351fde9a7873ccd4bd0f76bad7bb3e23d15b4d14d72a32a406a687`。
tarball 全部文件（strip_root 后）：

```
.gitignore  ChangeLog  Conn.c  GPL  List.c  Makefile  Makefile.in  README.md
_config.yml  commands.c  config.h.in  configure  configure.in  cstring.c
index.html  install-sh  pconsole.c  pconsole.sh.in  ssh.sh  stamp-h.in
terminal.c  images/screenshot.jpg
include/{Conn,List,commands,cstring,pconsole,terminal}.h
```

- 无 `tests/`、`test/`、`testsuite/` 目录
- `Makefile.in` 的目标只有 `all` / `neat` / `clean` / `mrproper` / `depend`(=`dep`=`.depend`) /
  `install` / `uninstall`——**没有 `check` 或 `test` 目标**，`make check` 未定义
- 无 automake `TESTS`/`check_PROGRAMS`，无 CUnit/check/criterion/gtest 绑定，无 dejagnu 集成
- `images/` 只有一张截图；`stamp-h.in` 是空文件

**上游静态测试数 N_static = 0**（单元 0 / 集成 0 / 其他 0）。

**第二步（可运行环境实际运行）**：上游 0 项，无可运行环境内可跑的上游用例，不存在"没环境"
的托词——是上游确实没有。适配后补全的 29 项全部**已实跑通过**（见「验证结果」）。

**第三步（适配后测试清单）**：29 个独立检查项，统一口径=**可单独判定成败并单独打印
`ok:`/`FAIL:` 的检查项**。

功能/消费者 25 项：

| 项 | 位置 | 断言 |
|----|------|------|
| S1×3 | test.sh | `bin/` 下 `pconsole`、`pconsole.sh`、`ssh.sh` 均存在且可执行 |
| S2/S2b | test.sh | `licenses/GPL` 已打包且确为 GPL 正文 |
| S3/S3b | test.sh | `pconsole.sh` 里 `prefix=`/`bindir=` 解析后指向**包目录**（配置期路径替换正确、可重定位） |
| S4/S4b | test.sh | `pconsole.sh` 无参数 → 退出码非 0 + 打印 usage 行 |
| S5×2 | test.sh | 两个脚本都过 `sh -n` |
| S6/S6b | test.sh | `ssh.sh` 无参数确实走到外部连接器分派（ssh 或 telnet）且不静默成功；脚本内两种分派形态都在（结构断言，见 notes「已知限制」） |
| F1 | pty harness | pty 下启动：banner `pconsole WJ101` + 进入 command mode + 正常退出（rc=0） |
| F2 | pty harness | `version` → `pconsole 1.2.0 WJ101` + 版权行 |
| F3 | pty harness | `help` → 完整命令表（attach/detach/list/connect/quit/exit/help/?/version/echo） |
| F4 | pty harness | `help warranty` → GPL 免责声明全文 |
| F5 | pty harness | `list`（无连接）→ `currently not attached to any terminal device` |
| F6 | pty harness | 未知动词 → `unknown command 'nosuchverb'` |
| F7 | pty harness | `attach` 无参数 → usage 行 |
| F8 | pty harness | `attach /no/such/tty` → 打印 `attaching /no/such/tty` + `No such file or directory`，不崩 |
| F9 | pty harness | `echo off/on/bogus` → 状态翻转回显 + 非法参数 usage |
| F10 | pty harness | `connect`（无连接）→ `currently not attached to any terminal device` |
| M1 | pty harness | **核心功能**：attach 一个真实 pty 后，主控端敲的按键经 `ioctl(TIOCSTI)` 注入目标终端（从 pty master 侧读到注入字节），`list` 显示该设备，attach banner 写到目标，rc=0 |
| M1b | pty harness | 走到 `put_conn()`（补丁点）说明 `seteuid()` 没有把进程打死：rc≠159 且无 `Bad system call` |

鸿蒙特有 4 项（rule12，N=4 ≥ 1）：

| 项 | 位置 | 针对的鸿蒙适配点 | 断言 |
|----|------|-----------------|------|
| H1 | pty harness（纯 Python 解析 ELF，不依赖 worker 上有 readelf） | 目标架构 | ELF64 小端且 `e_machine == EM_AARCH64(183)` |
| H2 | 同上 | R26 系统同名库 | `DT_NEEDED` 只有 `libc.so`，无任何同名系统 .so 被链入/投放 |
| H3 | 同上 | **E051 鸿蒙 seccomp 边界** | 启动路径退出码 ≠ 159 且 stderr 无 `Bad system call`（未打补丁的产物在此被 SIGSYS 直接打死） |
| H4 | 同上 | isatty 前置门 | 非 tty stdin 下退出码非 0，且是 pconsole **自己的**门控消息（`must be root` / `not a tty`），而不是被内核杀掉 |

## 四维测试账本

| 维度 | 数值 | 来源 |
|---|---|---|
| 上游静态声明 N_static | 0 | tarball 静态清点（文件清单 + Makefile.in 目标 + 无测试框架绑定） |
| 构建系统注册 N_registered | 0 | 无 `check` 目标，`make check` 未定义 |
| 实际执行 N_executed（上游） | 0 | 上游确无测试 |
| 未执行分类 | 0 | — |
| 消费者测试 N_consumer | 2 个文件 / **29 个检查项** | test.sh 13 项 + pconsole_pty_test.py 16 项 |
| 鸿蒙特有（rule12） | **4**（H1–H4） | 计入上述 29 项内，不重复计数 |

## 源码修改（补丁）

唯一补丁 `patches/0001-pconsole.c-seteuid-noop-guard.patch`（+2/-2，2 个 hunk）：

```diff
 	/* regain root privs */
-	if (seteuid(0)) {
+	if (geteuid() != getuid() && seteuid(0)) {
@@
-	if (seteuid(getuid())) {				/* drop root privs */
+	if (geteuid() != getuid() && seteuid(getuid())) {		/* drop root privs */
```

- 分类: `portability`，**不含任何平台宏** → 满足 R8「对非鸿蒙平台必须透明」与 PF5 补丁平台宏闸
- 语义等价性: `euid == uid` 时 `seteuid(...)` 按 POSIX 不改变任何 uid，跳过它是严格的空操作消除；
  真 setuid-root 二进制（`euid != uid`）仍走原路径并原样打印原错误
- 与既有先例的差异: 与 `archives/s/secpwgen/1.3` 的
  `0001-secure_memory_unix.c.patch`（+11/-0 单 hunk）**同一判据**，本包用 `&&` 短路形式
  写在原条件上而不是提前 `return`——`main()` 中间提前返回会打乱后续流程，两个 hunk 分别
  对应 `put_conn()`（每次注入按键的提权/降权）与 `main()`（启动期降权）
- 缩进沿用上游 tab 风格；不改动任何其他上游行为

## 依赖版本

**零外部依赖**。`requirements()` 为空：pconsole 只用 libc
（`unistd.h` / `fcntl.h` / `sys/ioctl.h` / `termios.h` / `sys/termios.h`），
链接产物 `DT_NEEDED` 实测只有 `libc.so`（H2 断言）。W0 预检
（`ci/scripts/preflight_check.sh pconsole/1.2.0`）因此无依赖可查，rc=0。

## 验证结果

### 1. W3 `conan create`（本地，profile `ohos-aarch64-wsl`，host/build 同 profile）

```
conan create archives/p/pconsole/1.2.0 --name=pconsole --version=1.2.0 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
→ rc=0
  configure: ANSI C header files... yes / fcntl.h... yes / sys/ioctl.h... yes /
             unistd.h... yes / working const... yes / st_rdev in struct stat... yes
  Created package revision 5164c2f0edd23c24751b89b58f634b25
  Package folder /root/.conan2/p/b/pconscea417c7ff7d6/p
  包内容: bin/pconsole  bin/pconsole.sh  bin/ssh.sh  licenses/GPL
```

configure 全部探测项一次通过，**无需**任何 config.guess 补丁、umask 改写（E011/E110/E125 均不触发）、
`--disable-nls` 之类的开关（本包无 gettext 依赖）。唯一编译告警是上游 `#include <sys/termios.h>`
的转发头 `#warning`。

### 2. test_package 实跑（29/29 通过）

```
PCONSOLE_SH_RESULT={"executed": true, "discovered": 13, "passedCount": 13, "failed": 0}
  S1_installed_pconsole / S1_installed_pconsole.sh / S1_installed_ssh.sh
  S2_license_packaged / S2b_license_is_gpl_text
  S3_pconsole_sh_prefix_is_package_dir / S3b_pconsole_sh_bindir_points_at_package_bin
  S4_pconsole_sh_usage_exits_nonzero (rc=1) / S4b_pconsole_sh_prints_usage
  S5_shell_syntax_pconsole.sh / S5_shell_syntax_ssh.sh
  S6_ssh_sh_reaches_connector_dispatcher (rc=255) / S6b_ssh_sh_has_both_dispatch_forms

PCONSOLE_PTY_RESULT={"executed": true, "passed": true, "discovered": 16,
                     "passedCount": 16, "failed": []}
  H1_elf64_aarch64 (class=ELF64 endian=little e_machine=183)
  H2_libc_only_needed (DT_NEEDED=['libc.so'])
  H3_no_sigsys_on_startup / H4_non_tty_invocation_refused (rc=255 'pconsole: not a tty')
  F1_banner_and_command_mode (rc=0) / F2_version_command / F3_help_command_table
  F4_help_warranty / F5_list_without_connections / F6_unknown_command
  F7_attach_requires_argument / F8_attach_missing_device_reports_errno
  F9_echo_toggle / F10_connect_without_connections
  info: TIOCSTI probe -> True (ioctl(TIOCSTI) accepted)
  M1_keystroke_multiplexing (attached=True list_shows_device=True banner_to_target=True
                             rc=0 injected_byte_in_target=True)
  M1b_no_sigsys_on_privilege_regain (rc=0)
```

### 3. 补丁区分度 A/B 实证（不依赖真机 seccomp）

用 `strace` 数特权 id syscall 次数——未打补丁 vs 已打补丁，**同一份源码、同一套工具链**各构建一次：

| 构建 | 特权 id syscall 次数 | 证据 |
|---|---|---|
| 未打补丁 | **1** | `setresuid(-1, 0, -1) = 0`（qemu-user 对 `seteuid(getuid())` 的宿主实现） |
| 已打补丁（本配方） | **0** | 只剩 `geteuid()`/`getuid()` 判定，syscall 根本没发出 |

即：判据 `geteuid() != getuid()` 在 euid==uid 时**确实把 syscall 消掉了**，这正是鸿蒙上
避免 SIGSYS 的机制。链接产物上 `seteuid` 符号两种构建都在（守卫是运行期判定，不是编译期消除），
因此**不能用符号表做判据**（与 secpwgen 结论一致）。

### 4. 反向验证（CI L1e 口径）：证明测试不是恒真

| 破坏方式 | test.sh | pty harness |
|---|---|---|
| 删掉 `bin/pconsole`（只留两个脚本） | 4 项 FAIL，rc=1 | `ABORT: ... missing or not executable`，rc=1 |
| 把 `bin/pconsole` 换成 `echo stub` 的假壳 | rc=1（S3/S3b 检出 prefix 指向别处） | 14/16 FAIL，rc=1（H1/H2 检出非 aarch64 ELF、F*/M1 全部检出无真实行为） |

### 5. 本地 CI 同源门禁

`CI_PACKAGES=archives/p/pconsole/1.2.0 CI_BRANCH=feat/pconsole-1.2.0 CONAN_PROFILE=ohos-aarch64-wsl
zsh ci/conan/build_and_test.sh` → **rc=0，Total 1 / Success 1 / Pass rate 100.0%**（完整日志见
`reports/w3-local-ci.log`，`conan create` 段见 `reports/conan-create.log`）：

| 阶段 | 结论 | 要点 |
|---|---|---|
| G0 | pass | 知识图谱完整性 |
| G0e | pass | 根目录白名单 |
| L0 | pass | L0a–L0i 结构/依赖/patches 格式/shell 变量/remote 硬编码；**L0j** 版本未占用（首次发布）；**L0k** commands.json 合法；**L0m** 目录结构；**L0n** 分支名 `feat/pconsole-1.2.0` 精确匹配 |
| KC | pass | 知识库质量门禁（草稿未泄漏进 graph/，无占位符） |
| JC | pass | JC1–JC6 全过（增量模式；本 PR 无运行时状态文件、无二进制、无 tarball、无隐藏文件、单软件原子） |
| L1 | pass | L1a test_package 被执行；L1b 有编译/运行痕迹；L1c 无上游 make check（上游确无测试）；**L1e 破坏性反向测试确认**（`[sabotage] bin/ moved away` → 测试确实依赖 pconsole） |
| L2 | pass | 非阻塞 warn：`pconsole --version/--help failed`（pconsole 无命令行版本开关，版本信息在 TUI 内的 `version` 命令，由 F2 断言覆盖）；`pconsole.sh --version OK` |
| L4 | pass | 补丁无 strcpy/sprintf/gets/strcat |
| L5 | pass | `bin/` 有内容 |

> 门禁脚本的 mirror-fallback 步骤会临时把 `conandata.yml` 改写成镜像 URL 列表，跑完再还原；
> 提交前已 `git checkout` 复原，仓库内的 `conandata.yml` 只有官方 URL（R39/PF7）。

## 框架侧发现（非本包问题，如实记录供主编修闸）

1. **PF8 与 PF9 对 CLI 工具包互相矛盾，导致合规配方无法通过 preflight**（本 PR 用
   `--no-preflight` 创建，已逐条实证）：
   - **PF8**（`scripts/ohc/preflight.py:check_recipe_static`）：CLI 包
     （`package_type="application"` 或 `bindirs` 非空）**必须**有
     `archives/<字母>/<包>/commands.json`（4 段路径），缺失即报「R38 必拦」。
   - **PF9**（`check_branch_and_paths`）：要求**所有** `archives/` 变更路径
     `len(f.split("/")) >= 5`，即 `archives/<字母>/<包>/<版本>/<文件>`。
     4 段的 `commands.json` 因此被判「变更路径缺版本目录层」。
   - 实证：带 `commands.json` → `PF9 失败`；临时移走 `commands.json` → `PF8 失败`。
     **两闸无法同时满足**。建议 PF9 对 `archives/<字母>/<包>/commands.json`
     （以及软件级 `manifest.yaml`/`README.md`）做白名单豁免。
2. **主仓 `main` 与 `origin/main` 不同步会让 preflight 扫全仓**：preflight 用
   `git diff <target>...<source>`，`target` 解析为**本地** `main` ref。
   若本地 `main` 落后（本例落后 3341 个文件变更），preflight 会把全仓历史违规
   一起报出来，淹没真实问题。建议改为 `origin/<target>...<source>`。
3. **CI 首轮构建 #65776 失败于 worker 资源耗尽，非配方问题**：
   `git-clone` 步骤报 `zsh:1: fork failed: out of memory`，
   `program finished with exit code 1`，`elapsedTime=0.148632`（0.15 秒即挂，
   远早于任何编译步骤）。另注：CI 按 SHA 去重，`/rebuild` 对同一 SHA 不会重新排队，
   需要新提交才能再次触发。

## 已知限制 / 注意事项

- **setuid-root 部署语义在鸿蒙上不成立**：pconsole 的设计前提是"setuid root 二进制"
  （README 建议 `chown root && chmod 4110`）。鸿蒙应用沙箱不给应用进程 root，
  setuid 位也不解决 seccomp 白名单问题，因此**本包在鸿蒙上的可用形态是"以 root 身份运行"**，
  不是"setuid 后普通用户运行"。这是平台能力边界，非适配缺陷；H4 断言把真实门控行为固化了。
- **`TIOCSTI` 的可用性因内核而异**：`TIOCSTI` 是特权 legacy ioctl，现代内核可用
  `dev.tty.legacy_tiocsti=0`（Linux 6.2 起默认）关掉。harness 因此**先探测再断言**：
  可用则断言注入字节真的出现在目标终端（真实多路复用），不可用则断言 pconsole 报出
  `ioctl()` 错误并干净 detach。两条分支都不是恒真断言。
- **`ssh.sh` 的运行期分支无法从外部固定**：脚本开头自己重置 `PATH`，`type ssh` 的结果
  取决于宿主是否装了 ssh。S6 因此只断言"确实走到外部连接器分派且不静默成功"，
  S6b 用结构断言确认 `type ssh` / `telnet` 回退 / `ssh $1 -p $2` 端口形态三种写法都在。
  这是本包唯一一处偏弱的断言，已如实标注。
- **`pconsole.sh` 带参数调用会无限自旋**（无 tty 时 `get_tty()` 不收敛），已明确排除在
  自动化测试之外；这是上游脚本缺陷，不在本次适配中修（会偏离上游行为）。
- **`-fomit-frame-pointer` 在 aarch64 上无意义**：上游 2001 年为 i386 写的 CFLAGS，
  clang 对 aarch64 接受但忽略。保留上游配置，未改。
- **`commands.json` 的 `binary` 字段为 `false`**：按 ARCHIVE-SPEC「适配中为 false，
  发布后改 true」；PR 合并、release 流水线上传后需改。
- **未执行 `conan upload`**：按任务要求停在 PR 阶段，不伪造 published 状态。

## 路径 B 判断

- **本次适配本身按路径 A（基础适配）申报**：唯一的 P0 适配点（E051 特权 id syscall）
  命中既有知识并按既有草稿的方案解决，没有产生新的可复用根因。
- **另附 1 条知识草稿**（提升权在主编）：
  `knowledge/drafts/DRAFT-pconsole-1.2.0-tiocsti-multiplex-setuid-deployment-boundary.kv` / `.md`
  填的是知识库**确实没有**的一格：本仓 drafts 中 `TIOCSTI` 命中数为 0，而"靠往别的 tty
  注入按键"正是 pconsole 的全部功能所在；草稿给出「先探测 TIOCSTI 能力再决定断言形态」
  与「setuid 语义工具在鸿蒙上的可交付边界」两条判定。
- 查重结论：`DRAFT-secpwgen-1.3-e051-*` 覆盖 seteuid 空操作守卫（本包**直接使用**其方案，
  不重复申报）；`DRAFT-E5xx-tui-app-pty-test-harness` 覆盖 pty 驱动 TUI 测试方法论
  （本包**直接使用**）；`DRAFT-8960-*` 覆盖"被测 CLI 读 stdin 到 EOF"（同类陷阱的另一形态，
  本包新增的是"驱动脚本 get_tty 不收敛"这一形态，写进新草稿的禁止做法）。
