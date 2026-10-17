# ocproxy 1.60 适配笔记

## 编译环境

- 构建系统：autotools（上游 tarball 只带 `configure.ac`/`Makefile.am`，无预生成 `configure`）
- 目标：OHOS / HarmonyOS PC aarch64（`os=OHOS`、`os.version=6.0`、`arch=armv8`、clang 15）
- 编译器：`/data/service/hnp/bin/clang`（由 `AutotoolsToolchain` 注入，配方不写死路径）
- 依赖：`libevent/2.1.13`（已发布 binary）；lwIP 与 lwIP unix contrib port 随 tarball vendored
- 构建工具依赖：`automake/1.18`（`tool_requires`，提供 `aclocal`/`automake`）
- 构建日期：2026-09-19
- 版本口径：任务 ID #9109 下发版本 `1.60`，上游 tag `v1.60`、`configure.ac` 声明 `1.60`，精确对齐。

## 编译步骤

配方 `build()` 的实际顺序：

1. `apply_conandata_patches()` —— 应用两个补丁。
2. `autoreconf --force --install --verbose`（`cwd=source_folder`）—— 生成 `configure`、
   `Makefile.in`、`config.guess`/`config.sub`/`install-sh`/`missing`/`depcomp`。
3. 就地去掉 `configure` 里 autoconf 生成的 `(umask 077 && mktemp -d "./confXXXXXX")`。
4. `Autotools.configure(args=["--build=aarch64-linux-ohos", "--host=aarch64-linux-ohos"])`。
5. `Autotools.make(args=["-j1"])` —— 设备内存紧张，且 HMDFS 上 make jobserver 的 FIFO 不可靠，固定单作业。
6. `Autotools.install(args=["-j1"])`，再补 `LICENSE`，并对
   `bin/ocproxy`、`bin/vpnns` 同时断言「存在 + 可执行位（`os.access(..., X_OK)`）」。

## 补丁

| 文件 | 内容 | 依据 |
| --- | --- | --- |
| `patches/0001-src-ocproxy.c.patch` | 给 `ocproxy` 补 `#include "config.h"`（`PACKAGE_VERSION` 来源）、`-V/--version`、`-h/--help`，并预扫描 `argv` 让这两个开关在 `VPNFD` 检查之前生效 | 上游 `vpnns` 1.60 已有同一形态的 `--version`/`--help`；缺这两个开关时打包与冒烟检查无法在无隧道环境下识别产物 |
| `patches/0002-src-vpnns.c.patch` | `vpnns` 的 `get_current_dir_name()` → `getcwd(NULL, 0)`（等价 POSIX 替换）；**行为变更**：无参运行改为打印用法并退出 1 | OHOS libc 既无该声明也无该符号；上游 `do_app()` 在无参时会经命名空间创建路径去启动 `$SHELL`，在本设备上先段错误（实测 rc=-31）。该守卫因此覆盖了上游「无参即交互 shell」的语义：vpnns 在本平台的定位是 `-- <command>` / `--attach` 运行器，隐式 shell 需要命名空间特权，包内测试改为断言「失败闭合」 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
| --- | --- | --- | --- |
| 1 | `configure: error: cannot guess build type; you must specify one` | `config.guess` 不认识 `uname -s` 报出的 `HarmonyOS`，而且它的编译探测需要 `cc`，设备上没有 | 显式传 `--build=aarch64-linux-ohos --host=aarch64-linux-ohos`（`config.sub` 认识这个三元组），两者相同 → configure 仍是 native 模式 |
| 2 | `./config.status: line 612: ./confiziVXM/subs1.awk: Permission denied` | autoconf 生成的 `configure` 用 `(umask 077 && mktemp -d)` 建私有临时目录；HMDFS 下该目录属性为 `drwx--S--- 2700`，连创建它的同一进程也写不进去 | 补丁：生成 `configure` 后就地去掉这两处 `umask 077`；`TMPDIR`/`TMP`/`TEMP` 同时指向 build 目录内的可写子目录 |
| 3 | `configure: error: cannot run C compiled programs` | `AutotoolsDeps` 只注入 `-L`/`-l`，rpath 分支仅在 macOS 生效，所以 configure 的 C 编译器可用性探针与 `AC_CHECK_LIB(event_add)` 都因加载器找不到 libevent 而失败 | 在 build 环境里把依赖包的 `lib` 目录前置到 `LD_LIBRARY_PATH`（用 `self.dependencies["libevent"].package_folder`） |
| 4 | `make` 报 `error: incompatible integer to pointer conversion assigning to 'char *' from 'int'`（`src/vpnns.c`） | `get_current_dir_name()` 是 GNU 扩展，OHOS libc 没有；隐式声明返回 int，被上游自带的 `-Werror=int-conversion` 拦下 | 补丁：改用 `getcwd(NULL, 0)`（POSIX，返回 malloc 分配的绝对路径，与后面的 `free(pwd)` 一致） |
| 5 | `vpnns` 无参运行时 coredump（rc = -31） | 上游 `do_app()` 在命令缺失时仍走命名空间创建路径，随后解引用不存在的命令 | 补丁：`optind >= argc` 时打印用法并返回 1（失败闭合） |
| 6 | `PACKAGE_VERSION` 未声明，编译失败 | `src/ocproxy.c` 从不 `#include "config.h"`，autoconf 只通过 `DEFS=-DHAVE_CONFIG_H` 提供它 | 补丁：补上 `#include "config.h"` |
| 7 | CI worker 上 `autoreconf: error: aclocal failed with exit status: 2` | 设备上 `aclocal` 来自 `~/.harmonybrew/bin`，而 CI worker 的 PATH 里没有系统 automake，`autoreconf` 找不到 `aclocal` | 加 `build_requirements()` → `self.tool_requires("automake/1.18")` |
