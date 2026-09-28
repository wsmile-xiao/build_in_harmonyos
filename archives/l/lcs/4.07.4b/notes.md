# lcs 4.07.4b 编译进度

**日期**: 2026-09-17（移植构建）/ 2026-09-18（CI 修复）
**状态**: ✅ conan create 成功（build/package/test 全 rc=0；CI 修复后完整复验通过）

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| 调查 | ✅ | SVN r738，GPL-2.0+，Autotools（无 configure，需 autoreconf -fvi） |
| source | ✅ | 无官方 tarball，conandata.yml 逐文件下载 188 个（!svn/bc/738 DAV URL，sha256 全部校验） |
| configure | ✅ | 平铺 ncursesw 补丁 + 显式 --prefix；探测出 -lncursesw，HAVE_WIDE_NCURSES + USE_NCURSES_W |
| make | ✅ | clang 15 / libc++ / -std=c++17 + -Wno-narrowing + _LIBCPP_ENABLE_CXX17_REMOVED_BINDERS |
| install | ✅ | bin/crimesquad + share/lcs/art/（38 个数据文件）+ share/man/man6 + .desktop |
| test | ✅ | PTY 真实启动：exit code 0、标题屏渲染 True、sitemaps 加载无失败、ESC 正常退出 |

## 上游信息

- Liberal Crime Squad，SourceForge `lcsgame` 仓库，SVN **r738**（4.07.4b 开发线；最新 SF 文件发布为 4.06，无 tarball）
- 构建系统：Autotools（configure.ac + Makefile.am，`AM_INIT_AUTOMAKE(foreign)`，仓库不含 configure/Makefile.in/config.h.in → `autoreconf -fvi` 引导）
- 形态：单可执行 `crimesquad`（C++03 代码，链接 ncursesw）
- 上游无 `make check`/测试目标；正式测试 = 真实运行游戏本体

## 源码集合说明

conandata.yml 收录 **188 个构建相关文件**：顶层 17 + src/ 129 + art/ 38 + docs/ 3 + man/ 1。
排除 `dev/`（开发草稿、.bak、PSD/PNG 美术源）与 `workspaces/`（VS 工程 + Windows exe）——非构建输入。
每个文件经 `!svn/bc/738` 固定修订版 DAV URL 下载，sha256 对新拉取校验。

## 真实根因与修复（最小修复，无 stub）

### 补丁 0001-accept-flat-ncursesw-layout.patch（configure.ac + src/includes.h）

上游 configure 假定发行版布局——宽字符 ncurses 装成 `<ncursesw/ncurses.h>` + `-lncursesw`，窄字符为 `<ncurses.h>` + `-lncurses`。Conan ncurses 包是**平铺布局**：单一 `include/ncurses.h` 本身就是宽字符头（含 cchar_t/add_wch），仅 `libncursesw.a`。于是探测链全灭：`AC_CHECK_HEADERS(ncursesw/ncurses.h)`→no → ncursesw 轮次跳过 → `AC_CHECK_LIB(ncurses, ...)` 找不到 libncurses.a → `AC_SEARCH_LIBS(initscr)` → `You need ncurses!`。

修复探测本身：ncursesw 轮次在子目录头缺席时接受平铺 `ncurses.h` 为宽字符头，`AC_CHECK_LIB(ncursesw, addch/add_wch)` 直探平铺库成功，`AC_SEARCH_LIBS` 自然得出 `-lncursesw`；includes.h 在 `HAVE_NCURSESW_NCURSES_H` 未定义时回退包含平铺 `<ncurses.h>`。不建 shim 目录、不加伪装宏。

### 编译器/标准库问题（recipe 内处理，非源码 stub）

1. **`-Wno-narrowing`**：cursesgraphics.h 以 chtype 宏（ACS_BULLET 等，unsigned int）初始化 int 数组成员，C++11 起 ill-formed narrowing（profile cppstd=17 下硬错误）；值均为非负小常量，关诊断即恢复 C++03 语义。
2. **`-D_LIBCPP_ENABLE_CXX17_REMOVED_BINDERS`**：shop.cpp 两处 `std::mem_fun`/`not1`（C++17 已移除）；libc++ 官方逃生舱宏恢复声明，源码零改动。
3. **`--prefix=<pkg>` 显式传入 configure**：OHOS conan 交叉构建默认 `--prefix=/`，会把 `$(datadir)=//share` 编译期固化进 `INSTALL_DATA_DIR` 宏，运行时找不到 `<pkg>/share/lcs/art/`（实测标题屏前即 "Failed to load sitemaps.txt!"）。同时 install 传 `DESTDIR=` 防 conan 自动 DESTDIR 与绝对 prefix 叠加成 `<pkg>/storage/<pkg>`。

## CI 失败修复（PR #10549，2026-09-18）

CI（原生 HarmonyOS，仅有 autoconf 套件）与开发机差异导致 create 在 autoreconf/configure 阶段失败，两个真实根因，均在 recipe 内修复：

1. **CI 不保证系统 aclocal**：`autoreconf -fvi` 报 `Can't exec "aclocal": No such file or directory`。修复：`build_requirements()` 加 `tool_requires("automake/1.18")`，`generate()` 里 `VirtualBuildEnv(self).generate()` 物化 conanbuild 环境——automake 的 bin（aclocal/automake）与其导出（ACLOCAL、AUTOMAKE、ACLOCAL_PATH、PERL5LIB）进入构建环境，`self.run("autoreconf -fvi", env="conanbuild")` 直接可用。不依赖系统工具、不硬编码任何路径。configure.ac 无 LT_INIT/AC_PROG_LIBTOOL（Makefile.am 仅 bin_PROGRAMS），故不需要 libtool tool_require。
2. **config.guess 不识别 HarmonyOS**：非交叉构建（build/host 同 ohos-aarch64 profile）时 AutotoolsToolchain 不传 `--build/--host`，autoconf 2.72 生成的 configure 无条件做 build-type 探测；automake/1.18 安装的 config.guess（2024-07-27）不认识 `uname -s=HarmonyOS`，报 `cannot guess build type; you must specify one`。修复：`generate()` 用 `_get_gnu_triplet(settings_build)` 得 `aarch64-linux-ohos` 并追加 `--build=` 到 `tc.configure_args`（bandwidthd/avr 同款做法）；stock config.sub 本就接受该三元组，无需 patch config.guess。

## 关键决策记录

1. **不用 AutotoolsDeps**：它导出 `LIBS=-lncursesw`，使 `AC_SEARCH_LIBS(initscr)` 判为 "none required"，`USE_NCURSES/USE_NCURSES_W` 均不定义 → `includes.h` `#error`。只用 AutotoolsToolchain，并手动把 ncurses 的 -I/-L 加进 extra_cxxflags/extra_ldflags（AutotoolsToolchain 本身不注入依赖路径），探测自然落到 `-lncursesw`。
2. **数据安装不加补丁**：`src/Makefile.am` 的 `crimesquad_CPPFLAGS = -DINSTALL_DATA_DIR=\"$(datadir)\"` 编译期注入，顶层 `dist_art_DATA` 装 38 个 art 文件到 `$(datadir)/lcs/art/`；prefix 正确后 `make install` 直接闭环（38=38=38 三向核对）。
3. **XML 加载是硬前置**：`main()` 在标题画面之前经 artdir 加载 7 个 XML（vehicles/clips/weapons/armors/masks/loot/creatures），任一失败即 `end_game()` 非零退出——标题屏渲染本身就是数据加载成功的断言。
4. **退出机制**：标题画面 `getch()==27`（ESC）→ `end_game()` → `endwin(); exit(0)`，干净退出无需存档。
5. **musl/宽字符**：musl `stdc-predef.h` 定义 `__STDC_ISO_10646__=201206L`，与 `HAVE_WIDE_NCURSES` 共同使 `CH_USE_UNICODE` 生效。
6. **libc++ 运行时**：NEEDED `libc++_shared.so` 在工具链 `/storage/Users/currentUser/usr/local/lib/aarch64-linux-ohos/`（profile 无 runenv，recipe runenv_info 与 test_package 均注入该 LD_LIBRARY_PATH）。
7. **dumpcaps.cpp 反斜杠路径**：开发工具、含独立 main()，上游 bin_PROGRAMS 不含它、从不构建——不修改。auto_ptr 160 处全在 `dev/`（未收录）。

## PTY 测试设计（真实运行）

- `TIOCSWINSZ` 设 **80x25**：不设 winsize 时 initscr 后画面渲染不完整
- 等待输出出现 `Liberal Crime Squad`/`Press ESC now to quit` 后发 **ESC**
- 子进程退出后 `os.read` 抛 `EIO` 是 PTY 正常行为——以 `waitpid` 取真实退出码
- 断言：exit code 0、标题屏文本出现（= 7 XML + sitemaps.txt 从安装目录加载成功）、无 "Failed to load sitemaps.txt!"、ESC 确已发送
- `TERMINFO` 指向 Conan ncurses 包 `share/terminfo`（十六进制布局，xterm 在 78/）；TERM=xterm
- 超时/kill 只判失败
- test_package 需**显式** `self.requires("ncurses/6.5")`：间接依赖 package_folder 为 None

## 验证结论（2026-09-17 实测）

- `conan create . -pr:h/-pr:b ohos-aarch64`：build/package/test 全 rc=0
- `conan create archives/l/lcs/4.07.4b -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`（2026-09-18 CI 修复后复验）：rc=0；configure 命令行含 `--build=aarch64-linux-ohos`，`checking build system type... aarch64-unknown-linux-ohos`，全日志无 "cannot guess"；test_package PTY 用例通过
- PTY 实测输出：`exit code: 0`、`title screen: True`、`quit hint shown: True`、`sitemaps failure: False`
- ELF：`ELF 64-bit LSB arm64 (aarch64)`，INTERP `/lib/ld-musl-aarch64.so.1`
- NEEDED：`libc++_shared.so` + `libc.so`（musl），**无 RPATH/RUNPATH**（零宿主路径泄漏）
- 包内数据：`bin/crimesquad` + `share/lcs/art/`（38 文件）+ `share/man/man6/crimesquad.6` + `share/applications/crimesquad.desktop`
- 二进制内嵌搜索路径首项 = `<pkg>/share/lcs/art/`（编译期 INSTALL_DATA_DIR 正确展开）

---

**编译结束**: 2026-09-17
**CI 修复**: 2026-09-18（automake/1.18 tool_requires + 显式 --build=aarch64-linux-ohos）
**最终状态**: built
