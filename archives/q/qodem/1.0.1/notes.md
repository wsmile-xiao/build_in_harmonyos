# qodem 1.0.1 — HarmonyOS PC 适配说明

- 包目录：`archives/q/qodem/1.0.1/`
- 构建系统：Autotools（`configure` + `make`，Autoconf 2.69 生成物）
- 语言：C（`lang-preflight` overlay 判定 `c`，源码 478 个文件中 C 占 470 = 98%）
- 类型：可执行程序（`package_type = "application"`，`archives/q/qodem/commands.json` 已声明）

## 1. 源码与版本

| 项 | 值 |
|---|---|
| URL | `https://downloads.sourceforge.net/project/qodem/qodem/1.0.1/qodem-1.0.1.tar.gz` |
| sha256 | `dedc73bfa73ced5c6193f1baf1ffe91f7accaad55a749240db326cebb9323359` |
| 大小 | 9959922 字节 |

**四路互证**（同一 sha256、同一 size）：

1. 项目官网下载页 <https://qodem.sourceforge.io/downloads.html> 的 Releases 表格直接列出
   `qodem-1.0.1.tar.gz` 的 SHA-256 = `dedc73bf…3359`（且写明 "The latest official release of
   Qodem is 1.0.1"）；
2. Homebrew `Formula/q/qodem.rb` 的 `url`/`sha256` 与之一致；
3. MacPorts `comms/qodem/Portfile` 的 `sha256` + `size 9959922` 与之一致；
4. 本机实际下载（curl -L 跟随 SourceForge 镜像跳转）`sha256sum` 逐字节一致、`size_download=9959922`。

**上游 git 无 tag**（如实记录，属判读要点）：

- `git ls-remote --tags https://codeberg.org/AutumnMeowMeow/qodem` → 0 行；Codeberg REST
  `/api/v1/repos/AutumnMeowMeow/qodem/tags` → `[]`，`/releases` → 404（官网导航指向的开发仓）。
- GitHub 上游 `klamonte/qodem`（README 里写的地址）与 `AutumnMeowMeow/qodem` → HTTP 404（已删）；
  `chinababu/qodem`、`qodem/qodem` → `git ls-remote` 128。
- `gitlab.com/AutumnMeowMeow/qodem`（nixpkgs 用的仓）在本设备被 Cloudflare 403 挡住，不可实核。
- conan-center-index 无 `recipes/qodem/`（`config.yml`/`conandata.yml`/`conanfile.py` 三路 404）。
- 结论：版本可得性按「**非 git 上游用官方发行渠道存在该版本可构建发行物**」判据成立
  （SourceForge 官方发布渠道 + 上表四路 sha256），URL 未做任何猜测。

## 2. 依赖（双源）

| 依赖 | 判定 | 证据 |
|---|---|---|
| ncurses(w) | **conan 硬依赖** `ncurses/6.6` | ① `conan list "ncurses/*" -r=ohpcd` → 6.4/6.5/6.6 三配方且 6.6 有 `os=OHOS, arch=armv8` 的二进制包；② 仓库内 198 个 conanfile 引用 ncurses（`acedb`/`aeolus`/`audtty`/`dialog`…），`aeolus` 同款 `self.requires("ncurses/6.6")`；③ 设备侧**没有** ncurses 头文件（`find /usr/include -name curses.h` 0 命中）只有 `/usr/lib/libncursesw.so.6`，所以不能走系统直链 |
| libgpm | 不可用 → `--disable-gpm` | configure 探测 `Gpm_Open in -lgpm` = no，不关掉会 `AC_MSG_ERROR` |
| libSDL | 不可用 → `--disable-sdl` | `SDL_Init in -lSDL` = no |
| libminiupnpc | 不用 → `--disable-upnp` | `upnpDiscover in -lminiupnpc` = no；关掉避免构建捆绑的 `lib/upnp` |
| X11/PDCurses | 不用 → `--disable-x11` | 平台无 X 栈 |
| cryptlib（内嵌 ssh） | 不用 → `--disable-ssh` | 上游默认即关闭，显式钉死，避免编进 `lib/cryptlib`（W0-3 的 ISA 命中就在这棵捆绑树里） |
| libutil / `forkpty` | 系统库直链，可用 | 探针 `clang probe.c -lutil` 编译运行 rc=0 |

ncurses 的**链接面验证**：conan 包只提供静态库（`libncursesw.a`/`libformw.a`/`libmenuw.a`/`libpanelw.a`），
`package_info.libs = ["formw","menuw","panelw","ncursesw"]`、`shared=False`，因此 qodem 最终
`readelf -d` 不应出现 `NEEDED libncursesw.so`（L4 复核）。

## 3. W0-3 平台可移植性

- **ISA 专属头**（`altivec.h`/`xmmintrin.h`/`immintrin.h`/`mmx.h`/`3dnow.h`/`arm_neon.h`）：
  全仓 grep **1 处命中**，且在捆绑的 `lib/cryptlib/crypt/aes_ni.h` 注释里（`--disable-ssh` 后该子树
  根本不进构建面）；自身 `source/` 0 命中。
- **glibc printf 钩子族**（`printf.h` / `register_printf_function`）：**0 命中**。
- 结论：不命中止损条件；实构建面（`make -j4`）编译链接全绿亦为反证。

## 4. termios / pty 一手探针（本任务选点核心）

`$TASK_DIR/w0/ptyprobe.c`（直接 clang 编译运行，未经任何包装）：

```
sizeof(struct termios)=60
TIOCGWINSZ=0x5413  TIOCSWINSZ=0x5414  TIOCSTI=0x5412
TIOCEXCL=0x540c    TIOCSCTTY=0x540e
open(/dev/ptmx)=3 ok → grantpt=0 → unlockpt=0 → ptsname=/dev/pts/1 → open(pts)=4 ok
ioctl(TIOCGWINSZ)=0
```

`$TASK_DIR/w0/fp.c` / `op.c`：

```
forkpty pid=17005 master=3   → child exited status=3   （rc=0）
openpty rc=0 m=3 s=4                                  （rc=0）
```

即：**OHOS 的伪终端栈（/dev/ptmx + grantpt/unlockpt/ptsname + openpty/forkpty + winsize/ioctl）
全部可用**，termios 结构体与 TIOC* 常量齐备 —— 这是 qodem 能在此平台上跑通全终端会话的基础。

## 5. 两处源码/构建补丁

### 0001-configure-hmdfs-umask.patch（HMDFS，E678 家族）

`configure` 末尾把 `config.status` 写出来，其中创建临时目录的代码是
``tmp=`(umask 077 && mktemp -d "./confXXXXXX")```。HMDFS 上带 `umask 077` 落盘的目录是
`drwx--S---`（0700、共享属主 20001006），而进程 euid=20020085、只在 `file_manager` 组里
→ other 位全无 → 写 `./confXXX/subs1.awk` 报 `Permission denied`：

```
configure: creating ./config.status
./config.status[744]: can't create ./confdOmDja/subs1.awk: Permission denied
config.status: error: could not setup config files machinery   ← configure rc=1
```

对照探针：同目录 `mkdir probe$$`（不带 umask 077）落盘 `drwxrws--x`（2771，组内可写）→ 写入成功。
补丁去掉两处 `umask 077 && `，`./configure` 即 rc=0 且 `Makefile`、`source/config.h` 正常生成。

### 0002-qodem-help-exit-and-getpwuid-null.patch（SIGSEGV + 信息型选项退出码）

同一个 `source/qodem.c` 里两处独立修改（补丁含 2 个 hunk）。

**① `getpwuid()` 解引用（SIGSEGV）** — `source/qodem.c:3450`：

```c
username = getpwuid(geteuid())->pw_name;
```

本设备 uid=20020085 不在 `/etc/passwd`（只有 root/bin/system/…/file_manager 等系统账号），
`getpwuid()` 返回 **NULL** → 解引用直接 SIGSEGV。三重证据：

1. C 探针 `getpwuid(20020085)=0`（返回 NULL），`pwd.getpwuid()` 在 Python 侧抛 `KeyError`；
2. `qodem --create-config X` 与整条终端会话一律 `rc=139`（SIGSEGV），而 `--help`/`--version`
   正常 —— 因为 `check_for_help()` 在取用户名**之前**就 `exit()` 了；
3. `-fsanitize=undefined` 构建给出定位：
   `source/qodem.c:3450:37: runtime error: member access within null pointer of type 'struct passwd'`
   → `#0 qodem_main / …/source/qodem.c:3450:37 / #1 main …:3910`。

补丁给 `getpwuid()` 加 NULL 兜底（依次回退 `$LOGNAME` → `$USER` → `"qodem"`）。

**② `--help` / `--version` 的退出码** — `qodem_main()` 原本 `exit(check_for_help(argc, argv))`，
而 `source/common.h` 定义 `EXIT_HELP 1`、`EXIT_VERSION 2`，于是两个信息型选项一律非 0 退出。
这既不符合 POSIX/GNU 约定（信息型选项应以 0 退出），也让本地 conan-verify 的 **L2 smoke 探针**
（`--version`/`--help`/`-V`/`-h` 任一返回 0 即 PASS）判 FAIL——实测 4 个探针分别返回
`2 / 1 / 10 / 1`。补丁改为 `exit(EXIT_SUCCESS)`。
CI 侧同名探针在 `ci/conan/build_and_test.sh` 中是 **non-blocking**（`[warn] … (non-blocking)`），
所以该差异只影响本地 conan-verify 的 L2 判定；`xqodem` 是 X11 启动脚本（OHOS 无 X，
`qodem-x11`/`uxterm`/`gnome-terminal` 全部找不到 → 恒 `exit 1`），L2 对它只给 warning 不阻断。

> 附带环境事实（留档，不进配方）：**ASan 的 SEGV 报告在本设备打不出来** —— `clang -fsanitize=address`
> 编的空指针解引用程序打印 `before` 后就是 `rc=139`、一行 sanitizer 输出都没有，与
> `notes/device-facts.md` §一.38（valgrind 的 SIGSEGV 永不投递给 handler）同型；**UBSan 不依赖
> 信号投递，是这类崩溃唯一可用的定位手段**。gdb/lldb 存在但 `ptrace: Permission denied`。

## 6. 运行时依赖：TERMINFO

conan `ncurses/6.6` 的 `package_info()` 里有
`runenv_info.define_path("TERMINFO", …)` / `TERMINFO_DIRS`，但 **test_package 图里 conan 会把
传递依赖标记为 `Skipped binaries`**，`runenv_info` 因此不会被聚合进 `conanrun.sh`，
`self.dependencies["ncurses"].package_folder` 也是 `None`。处置：test_package **直接
`self.requires("ncurses/6.6")`**，把 `…/share/terminfo` 作为参数传给 `test.sh`，由测试脚本
`export TERMINFO/TERMINFO_DIRS`。另外 conan 的 `VirtualRunEnv` 会把 `TERM` 钉成 `dumb`，
curses 程序无法使用，`test.sh` 检测到 `TERM` 为空或 `dumb` 时改成 `xterm`。实测：

| 场景 | 结果 |
|---|---|
| `qodem --exit-on-completion --capfile … uname` **不带** TERMINFO | `rc=10`（优雅失败，不崩溃） |
| 同上 **带** TERMINFO（无 tty、stdin=/dev/null） | `rc=0`，capture 文件写出被测命令输出 |
| 同上 **带** TERMINFO 并跑在真 pty 里 | `rc=0`，capture 与 pty 屏幕内容一致 |

## 7. 上游测试

上游**没有任何测试套件**（清点命令与结果）：

```
find . -name 'Makefile.am'                     → 1 个（仓库根，无子目录 Makefile.am）
grep -rn 'check_PROGRAMS\|^TESTS\|TESTS =' --include=Makefile.am .   → 0 命中
find . -maxdepth 3 -type d -iname '*test*'     → ./lib/cryptlib/test（--disable-ssh 后不进构建面）
```

⇒ N = 0，`make check` 无可执行内容。功能验证全部由 `test_package/`（11 项消费者断言）承担，
其中 4 项是**鸿蒙侧真·终端会话断言**（`forkpty` 起 shell → ncurses 渲染 → `--capfile` 回读比对）。
