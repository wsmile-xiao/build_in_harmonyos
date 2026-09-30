# zangband 2.7.5pre1 适配笔记

## 软件信息
- 名称: zangband
- 版本: 2.7.5pre1
- 上游: https://sourceforge.net/projects/zangband/
- 构建系统: 旧式 autoconf（configure.in，非 automake）+ 手写 makefile.in + 递归 make
- 产物: `bin/zangband`（ncurses/GNU Curses 终端前端）+ `share/games/zangband/lib/`（281 个游戏数据文件）

## 编译环境
- 构建系统: autotools（configure + makefile）
- 编译日期: 2026-09-30
- 编译器: clang 15（aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

```bash
# 1) 先构建期主机工具 tolua（用构建机编译器，见"源码修改"）
# 2) configure（交叉编译，关闭 X11/GTK/Tcl-Tk，注入 autoconf cache）
./configure --prefix=/usr \
    --with-x11=no --with-gtk=no --with-tcltk=no --with-setgid=no \
    --cache-file=<cache> \
    CPPFLAGS="-I<conan ncurses>/include" \
    LDFLAGS="-L<conan ncurses>/lib"
# 3) 移除自重建规则与无用 -lz，然后
make -j16 TOLUA_HOST=<host tolua> BUILD_CC=cc BUILD_CFLAGS="-O2 -w -I." BUILD_LIBS="-lm"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS SDK sysroot 只有运行期 stub `libncurses.so.6`，无 `curses.h`、无链接符号 | SDK 只随附运行期库 | 依赖仓库现有 `ncurses/6.6`（静态 `libncursesw.a` + 头文件 + terminfo）。实测 configure 后 `USE_GCU` 被定义、`LIBS` 含 `-lncursesw` |
| 2 | `configure: error: cannot compute sizeof (long int), 77` | 旧式 autoconf 的 `AC_CHECK_SIZEOF`/`AC_FUNC_*` 需要**运行**探测程序，交叉编译无法运行 | 通过 `--cache-file` 注入已知 aarch64/musl 结果（`ac_cv_sizeof_long_int=8`、`ac_cv_func_malloc_0_nonnull=yes` …、`ac_cv_search_initscr=-lncursesw`） |
| 3 | `configure: error: cannot find required auxiliary files: config.guess config.sub` | 上游 makefile/makefile.in 带自重建规则（`makefile: configure makefile.in`、`configure: configure.in`），会调 aclocal/autoheader/autoconf；但 tarball 不含 automake aux 文件 | 配方在 make 前去掉这两条重建前提（configure 已生成正确 makefile） |
| 4 | `Error loading shared library libz.so (needed by src/lua/tolua)` / `Error 127` | `src/lua/tolua` 是**构建期代码生成器**，却被用目标编译器构建成 aarch64 二进制，无法在构建机执行 | 补丁 0001：让 make 用 `BUILD_CC` 编译 tolua，并用 `TOLUA_HOST` 变量指向主机版二进制 |
| 5 | `clang: error: no such file or directory: 'src/l-*.c'`（且 make 报 Error 127 被忽略） | **隐蔽陷阱**：`tolua.c` 用 `strcpy(path, argv[0])` 推导 `basic.lua..doit.lua` 脚本目录，tolua 不在 `src/lua/` 内时会静默返回 0，make 误判成功 | 把主机版 tolua 输出到 `src/lua/tolua_host`（与 lua 脚本同目录） |
| 6 | 二进制多一个 `NEEDED libz.so` | `configure.in` 里 `AC_CHECK_LIB([z],[main])` 无条件把 `-lz` 加进 `LIBS`，但程序无任何 zlib 未定义符号（`llvm-nm -u` 验证） | 配方从生成的 makefile 中移除 `-lz`；修复后 `llvm-readelf -d` 只剩 `NEEDED libc.so` |
| 8 | CI worker 上 `Error 127`：`/system/bin/sh: /bin/bash: inaccessible or not found` | bash 路径随环境而变（本机 `/bin/bash`；OHOS 设备/CI worker 为 `/data/service/hnp/bin/bash`），配方硬编码 `/bin/bash` 导致找不到 | 配方改为优先沿用 profile 的 `CONFIG_SHELL`，回退 `shutil.which("bash")`，不硬编码路径 |
| 7 | `./configure: Bad substitution` | 上游 configure 是 2005 年产物，含 bash 专有语法（`${var//pat/rep}`），`/bin/sh`(dash) 不支持 | 配方强制 `CONFIG_SHELL=/bin/bash` 并用 `/bin/bash ./configure` |

| 9 | CI 上 `config.status` 报 `./confstatXXXXXX: Permission denied`，随后 `FileNotFoundError: .../src/makefile` | CI worker 的 HMDFS 共享盘不允许在源码树内创建 mode-0700 的临时目录；autoconf 固定用 `umask 077 && mktemp -d ./confstatXXXXXX`（相对路径，不受 `TMPDIR` 影响），于是 `config.status` 什么都写不出来，`makefile` 根本不存在 | 配方把「去掉 makefile 自重建前提」的修改提前到 **configure 之前**直接改 `makefile.in`（模板），并在 configure 之后检测 `makefile` 是否存在：缺失则依次用 `config.status makefile`、模板占位符替换兜底生成一份，保证 make 一定有可用 makefile |

## 源码修改

补丁 `patches/0001-makefile-host-tolua.patch`：修改 `src/makefile.zb`
- 把依赖 `VERBOSE` 的 `define TOLUA`（内含 `@ src/lua/tolua`）替换为 `TOLUA = $(TOLUA_HOST)`
- tolua 自身的构建规则改用 `$(BUILD_CC) $(BUILD_CFLAGS) ... $(BUILD_LIBS)`
- `$(LUAWSRCS): %.c: %.pkg src/lua/tolua $(TOLUALUAOBJS)` 去掉对目标架构 tolua 的依赖

自重建前提的移除在 **configure 之前**直接作用于 `makefile.in`（模板），避免被 `config.status` 重新生成 `makefile` 时覆盖；`-lz` 的移除则在 configure 之后作用于生成的 `makefile`（模板里是 `@LIBS@` 占位符，不含字面 `-lz`）。


### CI worker（HMDFS）下的 makefile 兜底

CI worker 的共享盘上，autoconf 的 `config.status` 无法在源码树内创建其 mode-0700
临时目录（`umask 077 && mktemp -d ./confstatXXXXXX`，相对路径、不受 `TMPDIR` 影响，
故 `Permission denied`），结果 `config.status` 什么都写不出来、`makefile` 不存在。
配方因此不再无条件依赖 `config.status` 的产物：

1. **configure 之前**先改 `makefile.in`：去掉 `makefile: configure makefile.in`
   与 `configure: configure.in` 两条自重建前提（上游不含 `config.guess`/`config.sub`，
   触发即失败）。这样无论 `config.status` 成败，模板本身就是可用的。
2. **configure 之后**若 `makefile` 缺失：先 `shutil.copyfile(makefile.in, makefile)`
   再跑 `./config.status makefile`；仍失败则直接以模板替换 `@CC@/@CPPFLAGS@/@LDFLAGS@/
   @LIBS@/@prefix@...` 等占位符生成最终 makefile。
3. `-lz` 的移除仍在生成的 `makefile` 上做（因为 `makefile.in` 里是 `@LIBS@` 占位符，
   不含字面 `-lz`）。

### 还需要兜底 `src/autoconf.h`

`config.status` 不只生成 `makefile`，还生成 **`src/autoconf.h`**（`angband.h` 第 20 行
`#include "autoconf.h"`）。HMDFS 下它同样写不出来，导致 `fatal error: 'autoconf.h'
file not found`。因此兜底逻辑还包含：

- 若 `src/autoconf.h` 缺失或为空，则读取上游 `src/autoconf.h.in`，把其中的
  `#undef NAME` 按本配方实测的探测结果渲染为 `#define NAME value`
  （命中）或 `/* #undef NAME */`（未命中）。
- 该结果取自 **aarch64/OHOS + 本配方 autoconf cache** 下 configure 的真实输出
  （共 **67 个 `#define`**），其中 `USE_GCU 1` 对应 ncurses 终端端口、
  `HAVE_LIBZ 1` 对应 configure 探测到的 zlib（链接期已由配方移除 `-lz`）。

实测：

| 场景 | 结果 |
|------|------|
| 正常路径 `conan create` | 退出码 0，包创建成功，产物仅 `NEEDED libc.so` |
| **模拟 CI 故障**（删除 `makefile` 且删除 `config.status`，强制走模板占位符兜底） | 退出码 0，包创建成功 |
| `local-validate-recipe.sh` | 退出码 0 |
| 消费者 e2e（qemu） | 5/5 PASS |
| 消费者 e2e（DAYU200 真机） | 5/5 PASS，exit_code=0 |

兜底实现要点（易错处，已修正）：

- `shutil.copyfile(makefile_in, makefile)` 会让 `makefile` **立即存在**，因此
  「模板替换」这一步不能写在 `copyfile` 之后的 `if not isfile(makefile)` 里，
  否则该分支永不执行、生成的 makefile 会残留全部 `@...@` 占位符。现改为两个
  **互相独立**的 `if not os.path.isfile(makefile)` 守卫。
- `@...@` 占位符清单必须与上游 `makefile.in` 实际内容一致（实测共 **14 个**：
  `@CC@ @CFLAGS@ @DEFS@ @CPPFLAGS@ @LDFLAGS@ @LIBS@ @prefix@ @exec_prefix@
  @bindir@ @datadir@ @GAMEGROUP@ @cygwin@ @TK_PORT@ @configure_input@`）。
  替换后断言无残留，否则直接判失败而非静默产出坏 makefile。
- `config.status` 可能根本不存在，`self.run("./config.status makefile")` 会抛
  `Error 127` **中断构建**；现已用 `try/except ConanException` 包住，降级到模板兜底。
- `-lz` 的移除改为**条件执行**：`config.status` 生成的 makefile 含 `-lz -lncursesw`，
  而模板兜底路径的 `@LIBS@` 已被替换为 `-lncursesw`（本无 `-lz`），两种情况都不报错。

## 依赖版本
- ncurses/6.6（仓库现有适配；静态宽字符库 `libncursesw.a`）

## 验证结果

```bash
# 真机 DAYU200 (OpenHarmony 6.0.0.47, aarch64)
./zangband -h
# -> Usage: angband [options]，含 "  -mgcu    To use GCU (GNU Curses)"，退出码 0
```

消费者端到端用例（链接游戏自身目标文件，非桩函数）真机 5/5 通过。
用例中的每一条断言均由 check() 依据真实返回值/可观测状态判定，不存在无条件打印
的 PASS（针对 AI 检视 #192246660 的修复，详见 reports/test-report.md）。

## 已知限制

- Zangband 的交互式终端前端依赖 terminfo 数据库。OHOS SDK sysroot、qemu 运行根
  以及 DAYU200 设备**均不提供 terminfo**（设备上 `hdc shell` 也无 TTY），因此
  `-mgcu` 交互界面无法在本环境端到端跑通；数据解析与 Lua 脚本引擎路径已用真机
  消费者用例覆盖（见 reports/test-report.md）。
- 上游**不提供测试套件**：`make test` 目标仅回显 makefile 变量（无断言），
  `lib/script/test.lua` 内容为注释 "Hack - this doesn't work now"，
  `src/lua/ltests.c` 是 Lua 内部调试模块而非测试程序。

## 交付物
| 文件 | 说明 |
|------|------|
| `bin/zangband` | 游戏主程序（aarch64，仅依赖 libc.so） |
| `share/games/zangband/lib/` | 281 个游戏数据文件（edit/script/file/apex/...） |
| `licenses/readme`, `licenses/z_faq.txt` | 上游许可与文档 |
