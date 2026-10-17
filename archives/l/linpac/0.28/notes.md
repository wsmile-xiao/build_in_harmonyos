# linpac 0.28 适配笔记

## 编译环境
- 构建系统: autotools（源码包自带预生成 configure 与 Makefile.in，autoconf 2.69 产出）
- 编译日期: 2026-09-28
- 编译器: clang / clang++（OHOS SDK 26.0.0.18，aarch64-linux-ohos）
- 目标平台: OpenHarmony / HarmonyOS PC (aarch64)
- 状态: built（conan-verify G0-G4 全通过）

> 注：本工程自带 `configure`/`Makefile.in`；镜像上没有 automake-1.11 / libtoolize，
> `autoreconf` 无法完成（`am__configure_deps` 会触发 `missing --run automake-1.11`
> 失败）。因此对 configure 的修改直接落在预生成的 `configure` 脚本上（仓库内已有
> 大量同类先例，如 activity-log 0003-configure-umask.patch）。

## 编译步骤

```bash
# 手工（探索阶段）
export CPPFLAGS="-I<ncurses包>/include -I$PWD/src/compat"
export LDFLAGS="-L<ncurses包>/lib"
./configure --prefix=/storage/Users/currentUser/tmp/lp-install3 --enable-static --disable-shared
make -j1
make install
make check      # 上游无测试：全部 "Nothing to be done for 'check'"

# Conan（配方内，build() 依次执行 configure / make -j1 / make -k check / make install DESTDIR）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 上游测试清点（R51 申报表）

| 项目 | 结论 |
|------|------|
| `grep -rn "TESTS\|check_PROGRAMS\|check-local" --include=Makefile.am .` | 0 命中（无任何测试目标） |
| `find . -type d -iname "*test*"` | 0 命中（无 tests/ 目录） |
| `make check` 实际执行 | exit 0，逐目录输出 `Nothing to be done for 'check'`（日志 `.ci_logs/`） |
| `src/applications/testapp.c` | LinPac 应用协议**人工演示程序**（连接运行中的 linpac 主机打印事件），未注册到任何 check 目标，非自动化测试 |
| 用例总数 / 通过 / 失败 / 跳过 | 0 / 0 / 0 / 0（上游无自动化测试入口） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: cannot guess system type` | 源码包内 config.guess 是 2009 版，不认识 `uname -s = HarmonyOS` | 补 `*:HarmonyOS:*:*` 分支；**注意必须在分支内 `echo "$GUESS"; exit`**——原脚本各分支用 `echo …; exit`，缺 exit 会继续走到需要编译 dummy.c 的兜底逻辑（且 `mktemp -d` + umask077 目录在 HMDFS 上不可写） |
| 2 | `configure: Invalid configuration 'aarch64-unknown-linux-ohos'` | 2009 版 config.sub 的 maybe_os 列表与内核-OS 白名单都没有 linux-ohos，`-linux*` 分支会把它改写成 `linux-gnu` | 在 maybe_os 列表与 OS 白名单各补 `linux-ohos*` |
| 3 | `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied` | E114：HMDFS 强制 setgid，`umask 077 && mktemp -d` 产生的 `drwx--S---` 目录属主也不可写 | configure 中两处 `umask 077` → `022` |
| 4 | `configure: error: cannot find an AX.25 listen program` | 上游 `AC_PATH_PROGS([LISTEN],[listen axlisten])` 找不到程序即 `AC_MSG_ERROR`；OHOS 没有 ax25-apps | 降级为 `AC_MSG_WARN` 并回填 `LISTEN="listen"`（宏必须有值，`windows.cc` 会 `execlp(LISTEN,…)`） |
| 5 | `AC_CHECK_LIB([ncurses],[main])` 失败 | Conan ncurses 只提供静态 `libncursesw.a`（无 `libncurses.a`/`libtinfo.a`/`libtermcap.a`） | configure 中 ncurses 检查与 termcap 回退链改为 `ncursesw`（`-lncursesw`），LIBS 亦随之 |
| 6 | `error: redefinition of 'sockaddr_storage'`（data.cc/calls.h/sources.cc） | OHOS sysroot 的 `<linux/socket.h>` 与 `<sys/socket.h>` 都定义该结构体（libc 侧由 `__MUSL__` 守卫，而 OHOS clang 未定义该宏） | 新增 `src/compat/linux/ax25.h` 兼容层，用 `-I` 前置：预置 `_UAPI_LINUX_SOCKET_H` + `__kernel_sa_family_t`，再 `#include_next <linux/ax25.h>` |
| 7 | `use of undeclared identifier 'SIOCPROTOPRIVATE'` | OHOS sysroot 的 `<linux/socket.h>` 未包含 `<asm/socket.h>`，`SIOCAX25*` 引用的 `SIOCPROTOPRIVATE` 在整个 sysroot 中不存在（属"头文件存在但 API 缺失"类问题） | 同上兼容层补 `#define SIOCPROTOPRIVATE 0x89E0`（asm-generic 标准值，0x89E0–0x89EF） |
| 8 | `member access into incomplete type 'WINDOW'`（linpac.cc / mail_screen.cc） | Conan ncurses 头文件按 `NCURSES_OPAQUE=1` 生成，`struct _win_st` 不暴露 | `stdscr->_maxx/_maxy` → `getmaxx()/getmaxy()`；`main_window->_clear = TRUE` → `clearok(main_window, TRUE)`（语义等价的公共 API） |
| 9 | 运行期 `Cannot create the lockfile /var/lock/LinPac.<uid>` | OHOS 上 `/var` 目录整体不存在，上游硬编码 FHS 路径 | `lock_file_name()` 按 `$LINPAC_LOCKDIR` → `/var/lock`（可写时）→ `$XDG_RUNTIME_DIR` → `$TMPDIR` 顺序选首个可写目录 |
| 10 | 补丁 dry-run 失败（calls.h 等） | 1998 年源码里夹着孤立 CRLF 空行；refresh-patch 用 difflib 文本模式（universal newlines）生成补丁，而 `patch` 按原始字节匹配，含 CR 行进入 ±10 行上下文即失败 | 这些文件不改源码，改用问题 6/7 的 `-I` 兼容层一次性覆盖 |
| 11 | `conan create` 报 `ISO C++17 does not allow 'register' storage class specifier`（linpac.cc:61） | OHOS profile 的 `compiler.cppstd=17`，clang `-std=c++17` 下 `register` 由警告升级为 hard error（本地手工编译默认 gnu++14 因此不复现） | 按知识图谱 **E293** 的处方：配方 `extra_cxxflags` 追加 `-Wno-error=register`，不改源码 |
| 12 | test_package 里锁文件“创建成功”但名字被截断成 `LinPa` | 上游全局缓冲 `char keyfile[64]` 装不下回落后较长的 `$TMPDIR` 路径，`snprintf` 静默截断 | 缓冲扩到 256，并在选目录时校验 `snprintf` 返回值（`>= len` 视为截断，跳过该候选） |
| 13 | 配方内 `make -k check` 报 `No rule to make target 'check'` | conan 用 `basic_layout` 做 out-of-source 构建，Makefile 在 build folder；首个版本误用 `cwd=self.source_folder` | 改为 `cwd=self.build_folder`（日志 `reports/upstream-make-check.log`：20 处 `Nothing to be done for 'check'`） |

## 源码修改（补丁）

- `0001-build-aux-config.guess.patch` — 增加 HarmonyOS 主机识别分支（含 `echo`/`exit`）。
- `0002-build-aux-config.sub.patch` — `linux-ohos` 加入 maybe_os 列表与内核-OS 白名单。
- `0003-configure.patch` — ncurses→ncursesw、termcap 回退→ncursesw、`listen` 缺省降级为警告、
  config.status 临时目录 `umask 077`→`022`。
- `0004-src-applications-mailer-mail_screen.cc.patch` — opaque WINDOW：`getmaxx/getmaxy/clearok`。
- `0005-src-compat-linux-ax25.h.patch` — 新增 `src/compat/linux/ax25.h` 兼容层（配合配方注入
  `-I<source>/src/compat`）。
- `0006-src-linpac.cc.patch` — 屏幕尺寸用公共 API + 锁文件目录可写回落（含全局锁路径缓冲 64→256）。
  另：配方 `generate()` 追加 `-Wno-error=register`（E293）与 `-I<source>/src/compat`。

未改动上游文件（同属 AX.25 头文件问题）: `src/calls.h`、`src/data.cc`、`src/sources.cc`
——由补丁 5 的 `-I` 兼容层统一覆盖。

## 依赖版本

- ncurses/6.6（`libncursesw.a` 静态宽字符库；制品仓已发布，R35 用 `conan install --requires` 验证可消费）
- 说明：上游 README 还列出 `libax25`/`ax25-apps`（运行期 AX.25 协议栈与 `listen` 工具），
  二者都不是链接期依赖：源码只用 `<linux/ax25.h>` 的 uapi 定义直接操作 `AF_AX25` socket，
  Makefile 中没有任何 `-lax25`，`listen` 仅作为可选外部程序被 `execlp` 调用。

## 验证结果

```bash
# 手工构建
$ ./configure --prefix=… --enable-static --disable-shared    # exit 0
$ make -j1                                                   # exit 0
$ make install                                               # exit 0
$ make check                                                 # exit 0（Nothing to be done，无测试）
$ HOME=… TERM=xterm libexec/linpac/linpac </dev/null         # 输出 "LinPac version 0.28 (Sep 29 2026) by KI6ZHD"
$ ls $TMPDIR/LinPac.*                                        # 锁文件落在可写运行目录（OHOS 无 /var/lock）

# Conan 流程
conan-verify: G0 预构建 / G1 配方完整性 / G2 conan create / G3 系统同名库隔离 / G4 产物完整性 —— 全部通过
test_package: 8 项断言全部通过（含"锁文件必须落在可写运行目录"鸿蒙特有断言）
```

## 交付物（package 目录）

| 目录 | 内容 |
|------|------|
| `bin/` | `linpac` 上游启动脚本（首次运行生成 `$HOME/LinPac` 个人配置） |
| `libexec/linpac/` | 终端本体 + 30 余个 LinPac 应用协议辅助程序（`mail`/`getmsg`/`telnet`/`w`/`mheard`/`logbook`/`testapp` …） |
| `lib/` | 插件 API 静态库 `liblinpac.a`、`libaxmail.a` |
| `include/linpac/` | 插件开发头文件 `lpapp.h`/`tevent.h`/`axmail.h` |
| `share/linpac/` | 宏（6 种语言）、码表 `*.ctt`、编码表、`station.data`、文档 |

## 已签名的限制与说明

- **AX.25 运行时能力依赖内核协议栈**：LinPac 的全部链路功能（连接/断开/监视/`/proc/net/ax25`
  状态）依赖 Linux AX.25 协议栈。OpenHarmony 内核不提供该协议栈，`SIOCAX25GETINFO` 等 ioctl 会
  失败；上游代码对此已有容错（返回 false / 显示 unknown），不会崩溃。本适配保证构建、链接、
  启动与界面初始化在 OHOS 上正确。
- **`listen` 监视窗口不可用**：OHOS 无 `listen`/`axlisten` 程序，`LISTEN` 宏回退为 `"listen"`
  （PATH 查找），运行该窗口时报 `Error: Cannot exec LISTEN`。
- **`bin/linpac` 启动脚本**：其 shebang 为 `#! /bin/bash` 且内嵌交互式问答；本适配不做修改
  （属上游交互体验），自动化验证使用 `libexec/linpac/linpac`。
- **AX.25 "new" 结构体探测保持上游行为**：上游 `configure.ac` 的探测代码写作
  `ax25_info_struct i;`（缺少 `struct` 关键字），在任何平台都会失败，因此 `NEW_AX25`
  从未被定义；本适配**有意不改动**该探测，保持与上游发行版一致的行为（`#ifndef NEW_AX25`
  分支编译通过并与上游二进制同语义）。
---

**编译结束**: 2026-09-29 09:56
**最终状态**: built
