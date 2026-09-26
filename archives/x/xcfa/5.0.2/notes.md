# xcfa 5.0.2 适配笔记

## 编译环境
- 构建系统: autotools（上游 tarball 自带 `configure`/`Makefile.in`，无需 automake/autoconf 自举）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4（OHOS SDK，target aarch64-linux-ohos）
- 目标平台: HarmonyOS PC / OpenHarmony aarch64（musl libc）
- 状态: built（conan create 本地通过；test_package 5+14 断言全绿）

## 源码与版本核验

| 项 | 值 |
|---|---|
| 官方源码 | https://download.tuxfamily.org/xcfaudio/xcfa_download/src/xcfa-5.0.2.tar.gz |
| SHA256 | 37cb7cbf6707d02b0e2082e49e3a8194b6d2c6cfecd2747f78b1a682c00a6815 |
| 大小 | 1091301 字节（与 Debian 源码包 `xcfa_5.0.2.orig.tar.gz` 的 sha256 逐字节一致，后者 5.0.2 的校验和见 `xcfa_5.0.2-4.dsc`） |
| 上游站点 | http://www.xcfa.tuxfamily.org/（作者已声明停止维护，发布目录仍可访问） |

> 上游站点入口 `http://download.tuxfamily.org/xcfaudio/xcfa_download/src/` 同时提供
> 4.0.x~5.0.2 的官方 tar.gz，5.0.2 为最后一版（2015-05-18）。Debian/Ubuntu 与
> deb-multimedia 分发的是同一份 orig tarball。

## 依赖（全部经 `conan download ... -r=ohpcd --only-recipe` 核验，日志 `.ohc/xcfa-logs/w0-deps-check.log`）

configure.ac 的强制依赖（缺失即 `AC_MSG_ERROR`）：

| configure 探测 | 依赖包 | 类型 |
|---|---|---|
| `PKG_CHECK_MODULES(gtk+-3.0 cairo glib-2.0 gthread-2.0)` | gtk/3.24.43 | 头文件+库（pkg-config） |
| `AC_CHECK_LIB([tag_c], [taglib_file_new])` | taglib/1.13.1 | 静态库 libtag_c.a（1.x 才有 C 绑定） |
| `AC_CHECK_LIB([asound], [snd_pcm_open])` | alsa-lib/1.2.16 | 库 |
| `AC_CHECK_LIB([curl], [curl_easy_init])` | curl/8.15.0 | 库 |
| `AC_CHECK_LIB([vte-2.91], [vte_terminal_feed])` | vte/0.74.2 | 库 |
| `src/Makefile.am` LDADD `-lX11`、`poche*.c` 包含 `<X11/Xlib.h>` | libx11/1.8.13 + xorgproto/2025.1 | 库 + 头文件 |
| taglib 静态库的 zlib 符号 / glib 的代理 libintl / C++ 运行时 | zlib/1.3.1.1（override）、glib 传递依赖、libc++ | 库 |

## 编译步骤（真实命令）

```bash
# 1) 依赖环境（等价于配方 generate() 的产物）
conan install <deps-conanfile> -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
source conanbuild.sh                     # CC/CFLAGS/CPPFLAGS/LDFLAGS/LIBS/PKG_CONFIG_PATH

# 2) E007：替换 OHOS 不识别的 config.guess/config.sub（自包含 OHOS-aware 版本）
#    HMDFS：预置 PWD、configure 的 ac_pwd 回退、umask 077→022

# 3) 配置 + 编译 + 安装
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
make check
```

产物：

```
bin/xcfa                        GTK3 图形界面（1.9 MB）
bin/xcfa_cli                    命令行工具（1.4 MB）
share/xcfa/glade/*.glade        6 个 GtkBuilder UI
share/pixmaps/xcfa/*.png|*.xpm  20 个图标 + 3 个顶层图标
share/applications/xcfa.desktop / share/man/man1/xcfa.1、xcfa_cli.1.1
```

## 遇到的问题与解决方案（首个真实错误 → 根因 → 最小修复）

| # | 现象（首个真实错误行） | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `configure: error: cannot guess build type; you must specify one`（config.guess 2008-01-23 版不认识 `uname -s` = HarmonyOS） | 上游 config.guess/sub 早于 HarmonyOS（E007） | 配方 build() 在 configure 前用自包含 OHOS-aware 版本替换 config.guess/config.sub（aris/adms 同款），不改源码树 |
| 2 | `checking for taglib_file_new in -ltag_c... no` → `ld.lld: undefined symbol: TagLib::FileRef::create` | AC_CHECK_LIB 只链 `-ltag_c`，静态 libtag_c.a 还需要 `libtag.a` 与 libc++；且 taglib 的 libdir 不在搜索路径 | generate() 注入各 AC_CHECK_LIB 依赖的 `-I/-L`，并把 `-ltag -lz -lc++` 放进 `LIBS`（configure 会保留初始 LIBS 且排在链接行末尾） |
| 3 | `alsa_audio.c:44: fatal error: 'alsa/asoundlib.h' file not found`（首次由配置阶段进入编译阶段） | configure.ac 在 debug/ansi 分支整体重写 CFLAGS，注入到 CFLAGS 的 `-I` 全部丢失 | 所有构建期 flag 改经 `CPPFLAGS` 注入（configure 不覆盖 CPPFLAGS） |
| 4 | `poche.c:45: fatal error: 'cairo-xlib.h' file not found` | OHOS 制品仓 cairo/1.18.4 关闭 xlib 后端（`xlib=disabled`），无 cairo-xlib.h；而 poche*.c 的该包含是死包含（全树无 `cairo_xlib_*` 调用） | 补丁 0001-0005：删除 5 个文件里未使用的 `#include <cairo-xlib.h>` |
| 5 | `X11/Xlib.h:44: fatal error: 'X11/X.h' file not found` | Xlib.h 依赖 xorgproto 的 `<X11/X.h>`；xorgproto 作为 libx11 的传递依赖在 `generate()` 中 `package_folder` 为 None | 显式声明 `xorgproto/2025.1` 为直接依赖并联通其 include 目录 |
| 6 | `win_vte.c:121: error: incompatible integer to pointer conversion assigning to 'GtkWidget *' from 'int'` | configure 只按硬编码 `/usr/include[/vte-2.91|/vte-2.90]/vte/vte.h` 判定头文件位置，Conan 提供的头文件不在其中 → vte 声明全部缺失 | 补丁 0006：`win_vte.c` 头文件探测增加 `#elif defined(HAVE_VTE) → #include <vte/vte.h>` 通用回退分支 |
| 7 | `ld.lld: error: duplicate symbol: StatusBar`（链接期） | 2015 年代码用 tentative definition 共享全局变量；clang 15 默认 `-fno-common` | CPPFLAGS 注入 `-fcommon`（aris 同款） |
| 8 | `ld.lld: error: undefined symbol: g_libintl_bindtextdomain / g_libintl_gettext ...` | glib 包内的 `<libintl.h>` 是代理头（gettext→g_libintl_gettext），实现是 glib 私有的 libintl.so.8 | `LIBS` 增加 `-lintl` 并把 glib libdir 加入 `-L`；运行期（configure 的 sanity check）把 glib libdir 前置到 `LD_LIBRARY_PATH` |
| 9 | `src_cli/get_info.h:31: error: unknown type name 'uint'` | OHOS/musl 的 `<stdio.h>` 不再间接引入 `<sys/types.h>`，glibc 的 `uint` 兼容类型不可见（E113 同类问题） | 补丁 0008/0009：`tags.h`、`get_info.h` 显式 `#include <sys/types.h>` |
| 10 | `ld.lld: error: undefined symbol: get_current_dir_name` | `get_current_dir_name()` 是 GNU 扩展，OHOS libc 未实现（源码仅前向声明后调用） | 补丁 0007：用可移植的 `getcwd(NULL, 0)` 提供本地静态实现 |
| 11 | 制品内出现 Conan 构建目录绝对路径（`__FILE__` 被 PRINT 宏写入 .rodata） | 上游 PRINT/PRINT_FUNC_LF 宏内嵌 `__FILE__`；编译器还记录 DWARF comp_dir | CPPFLAGS 注入 `-ffile-prefix-map/-fdebug-prefix-map/-fmacro-prefix-map=<source|build>=.`（libnxml/libmrss/libgcrypt 先例） |

## 源码修改（补丁）

9 个补丁（`patches/`，全部为通用可移植性修复，无 `__OHOS__` 等平台宏，无平台条件编译）：

| 补丁 | 内容 |
|---|---|
| 0001~0005 | `src/poche*.c`：删除未使用的 `#include <cairo-xlib.h>`（OHOS cairo 无 xlib 后端） |
| 0006 | `src/win_vte.c`：vte 头文件位置探测增加 `HAVE_VTE` 回退分支 |
| 0007 | `src_cli/main.c`：`get_current_dir_name()` → `getcwd(NULL, 0)` 本地实现 |
| 0008/0009 | `src_cli/get_info.h`、`src_cli/tags.h`：显式包含 `<sys/types.h>`（uint） |

## 设计取舍

- `package_type = application`：产物含 2 个可执行文件（xcfa / xcfa_cli），按 R38 在软件级
  目录声明 `commands.json`（type=tool，versions.5.0.2.ref=xcfa/5.0.2）。
- 动态链接：gtk/vte/taglib/alsa/curl 均非系统同名库，交由 Conan 管理依赖链（R26），
  二进制不写 RPATH/RUNPATH，运行期由 `conanrun` 环境解析。
- 依赖注入全部使用 Conan 包目录路径与 `LIBS`/`CPPFLAGS`/`LDFLAGS`，未注入任何共享系统前缀（R49）。
- NLS（gettext 翻译）保持上游默认探测结果：OHOS 无 gettext 工具链 → `USE_NLS=no`，
  不安装 `po/` 翻译；程序可用（源码字符串为法语/英语原文），不影响功能与测试。

## 上游测试入口核验（R51 三步法第一步）

清点证据（真实命令与输出见 `reports/test-report.md`）：

- `grep -rn "TESTS|check_PROGRAMS|check_SCRIPTS|check_LTLIBRARIES" --include=Makefile.am --include=Makefile.in .` → **无任何匹配**
- 源码内测试宏 `assert(`/`TEST_CASE`/`CU_TEST`/`BOOST_AUTO_TEST` → **0 处**
- `find . -maxdepth 2 -type d -iname "*test*"` → **无 tests/、test/ 目录**
- `make check`（真实执行，exit 0）→ 各子目录均输出 `Nothing to be done for 'check'`，**0 个用例执行**

结论：**上游没有自动化测试套件**（不是"未运行"，而是"不存在"）。

## 测试四维账本

| 维度 | 数量 | 说明 |
|---|---|---|
| N_static（上游静态声明） | 0 | 无 TESTS/check_PROGRAMS 声明 |
| N_registered（构建系统注册） | 0 | `make check` 无目标 |
| N_executed（实际执行） | 0 | 上游无测试可执行 |
| N_consumer（新增消费者测试） | 19 | test.sh 5 条 + test_ohos.sh 14 条（鸿蒙特有） |

## 验证结果

```bash
# 真实构建 + 打包 + 消费者测试（一次命令覆盖 recipe/package/test）
conan create archives/x/xcfa/5.0.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → exit 0；test.sh 5/5 PASSED；test_ohos.sh 14/14 PASSED
# 日志：.ohc/xcfa-logs/conan-create-3.log

# 上游测试入口
make check   # exit 0，全部 "Nothing to be done for 'check'"

# 运行期抽查（conanrun 环境）
xcfa --version            # → xcfa 5.0.2 / Gtk version = 3.43.24 / Glib version = 2.0.84
xcfa_cli                  # → 环境报告 sysname HarmonyOS / machine aarch64
xcfa_cli -i sample.wav --info_files   # → frequency = 8000 / quantification = 16 / time = 00:00:01
```

## 注意事项

- 上游站点已停止维护：源码 URL 指向其官方发布目录（https，仍在服务），
  若该目录下线需改用 Debian orig tarball（sha256 一致）。
- xcfa 的 UI（`share/xcfa/glade/*.glade`）按上游设计可在运行期通过
  `XDG_DATA_DIRS=<prefix>/share` 定位（`lib/xdg.c`），不依赖编译期 `/share` 绝对路径。
- GUI 需要显示服务；无显示服务时会打印 `cannot open display` 并以 rc=1 优雅退出（已纳入鸿蒙测试）。
- `xcfa_cli` 的 `--version` 不是合法选项（上游只实现 `--help`），测试中只断言 `--help`/环境报告。
---

**编译结束**: 2026-09-25 21:45
**最终状态**: built
