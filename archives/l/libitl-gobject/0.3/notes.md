# libitl-gobject 0.3 适配笔记

## 编译环境
- 构建系统: autotools（上游 tag 归档不含任何生成文件，需先做 autoreconf 引导）
- 编译日期: 2026-09-14
- 编译器: clang 15.0.4（OHOS SDK），target aarch64-unknown-linux-ohos
- Profile: `ohos-aarch64`（host/build 同一 profile，非交叉）
- 状态: built（本地 `conan create` 全绿，含 test_package 40 条断言）

## 编译步骤

本配方把上游 README 里的人工步骤全部固化到 `build()` 中，顺序如下：

1. `apply_conandata_patches()` —— 4 个补丁（见下）。
2. `_run_autogen()` —— **分步**引导 autotools（不是一条 `autoreconf -fi`）：
   1. `aclocal --force`（`ACLOCAL_PATH` = `<src>/m4` + libtool/share/aclocal + automake/share/aclocal）
   2. `libtoolize --copy --force --install`（`_lt_pkgdatadir` 指向自建 build-aux/m4/libltdl 目录）
   3. `autoconf -o configure configure.ac`
   4. `automake --add-missing --copy --no-force`
3. `_patch_harmonyos_config_scripts()` —— E007：把新生成的 `config.guess`/`config.sub`
   补上 HarmonyOS 识别（见「遇到的问题」#3）。
4. `_restore_autotools_script_modes()` + `_drop_umask_077()` —— 见「遇到的问题」#4/#5。
5. `sh "<src>/configure" <autotools._configure_args>` —— 关键参数：
   `--enable-shared --disable-static --prefix=... --disable-introspection`
   `CPPFLAGS=-I<libitl>/include -I<glib>/include -I<libtool>/include -I<libitl>/include/itl`
   `LDFLAGS=-L<每个依赖的 libdir>`
6. `self._make(autotools)` → `make -j1`（OHOS 下把输出绑到文件，见问题 #13）→ `make check`（上游零注册用例，守住 check 机制）。
7. `Autotools.install()` → 删除 `*.la` → 复制 COPYING 到 licenses/。

`conan create archives/l/libitl-gobject/0.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --build="libitl-gobject/*"`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure.ac` 里 `PKG_CHECK_MODULES` / `GOBJECT_INTROSPECTION_CHECK` 在 autoconf 阶段报 possibly undefined macro | `pkg.m4` 与 `introspection.m4` 不在构建机默认 aclocal 搜索路径，上游 m4/ 目录为空 | 把两个宏文件 vendoring 进配方 `m4/`，`export_sources()` 随源导出，`ACLOCAL_PATH` 前置该目录 |
| 2 | `autoreconf -f -i` 整条跑失败（autoconf.m4f 加载冲突） | OHOS HMDFS 下 autoreconf 并行/缓存加载 m4 冻结文件冲突 | 改用 `_run_autogen()` 分步调用 aclocal/libtoolize/autoconf/automake（同 archives/a/abiword-plugin-gdict） |
| 3 | `configure: error: cannot guess build type; you must specify one`（UNAME_SYSTEM=HarmonyOS） | automake 1.18/libtool 2.5.4 自带的 config.guess 不认 HarmonyOS | **E007**：不注入 `--build/--host`（R1，且会被误判成交叉编译跳过全部 AC_RUN_IFELSE），改为补 config.guess（`__OHOS__` LIBC 分支 + `*:HarmonyOS:*:*` 识别块）与 config.sub（`ohos-linux` 简写 / `ohos*` / `linux-ohos*` 校验项），全部带幂等守卫。脚本优先找 `scripts/patch-autotools-ohos.pl`，找不到时走配方内 Python 移植版（CI 不导出 `CI_REPO_ROOT`，实际走移植版） |
| 4 | `sh: <build>/configure: Permission denied`（ConanException: Error 126） | autoconf 现生成的 `configure` 在 HMDFS 上落盘后执行位不生效/被沙箱拒绝 | ①`_restore_autotools_script_modes()` 补回 configure/config.guess/config.sub/install-sh/missing/compile/depcomp/ltmain.sh 的可执行位（同 archives/p/pcre2）；②用 `sh "<abs>/configure"` 显式调用，只依赖读权限（同 gdict/pcre2/wv） |
| 5 | `config.status: cannot create ./confXXXXXX/subs1.awk: Permission denied`（潜在） | **E011/E114**：HMDFS 上 `umask 077 && mktemp -d` 建出的 2700 目录自身不可写 | `_drop_umask_077()` 把生成文件里的 `umask 077` 改成 `022`（同 gdict/libiodbc2），在 configure 运行前改，config.status 一并继承 |
| 6 | `checking whether we are cross compiling... error: cannot run C compiled programs`（rc=127） | 我最初把 `<glib>/lib/libintl.so` **绝对路径**写进 LDFLAGS。LDFLAGS 会作用于 configure 的每个探针链接，于是探针 `conftest` 带上 DT_NEEDED `libintl.so.8`，而 configure 阶段只有 conanbuild 环境（无 conanrun 的依赖 libdir），加载器报 `Error loading shared library libintl.so.8` 退出 127，configure 误报成“不能运行编译产物”（E064/E505） | **LDFLAGS 只放 `-L` 搜索路径，绝不放具体库文件**。真实库链接需要的 `-lintl` 本来就由 `glib-2.0.pc` 的 `Libs:`（经 gobject-2.0 的 `Requires:` 展开）提供 |
| 7 | `src/Makefile.am` 的 glib-mkenums 规则报 `FileNotFoundError: itl-gobject-enums.c.in` | 两条**手写**规则用 `$@.in` / `itl-gobject.h` 相对名，没有 automake 自动补的 `$(srcdir)`；conan `basic_layout` 是 VPATH（out-of-tree）构建，make 的工作目录是 `build-<type>/src` | 补丁 0003：两处改为 `$(srcdir)/$@.in` 与 `$(srcdir)/itl-gobject.h`，源码内构建与 VPATH 构建都成立 |
| 8 | `make` 调 `glib-mkenums` 报 `/usr/bin/perl: bad interpreter: Permission denied`（Error 126） | PATH 里 `/data/service/hnp/bin/glib-mkenums` 是 perl 脚本、shebang 指向不存在的 `/usr/bin/perl`，把我准备的包装器挤到了后面。profile `[buildenv]` 用 `PATH=+(path)` 前置 `/data/service/hnp/bin`，且行序在配方 `buildenv_info` 之后生效，所以单纯 `buildenv_info.prepend_path` 抢不到最前 | `_export_toolchain_env()`（conanbuild.sh 里最后 source 的脚本）里前置包装器目录；同时**不再**在该脚本里重复前置 `/data/service/hnp/bin`（它本来就在基础 PATH 上），否则会把包装器再挤回去。包装器用 `sys.executable + runpy` 跑 glib 包内的 `bin/glib-mkenums`（同 archives/a/atk） |
| 9 | test_package 的 CMake try-compile 报 `make[1]: .../clang-wrappers/clang: Permission denied`（Error 127） | 编译器包装脚本在 `build()` 里刚写完就被 make 执行，HMDFS 上该 exec 偶发 EACCES（同 #4 的同一类问题） | 直接**去掉包装器**：profile `[buildenv]` 已经把 SDK `llvm/lib` 放进 `LD_LIBRARY_PATH`（lld 需要的 libxml2.so.16，E120），裸 clang 足够（同 #6 的最小化思路） |
| 10 | test_package 报 `fatal error: 'itl-gobject.h' file not found` | 上游 `libitl_gobject_ladir = $(includedir)/itl`，头文件装在 `include/itl/`，而 `cpp_info.includedirs` 默认只有 `include`（E217 同款） | `includedirs = ["include", "include/itl"]`，与上游 `.pc` 的 `Cflags: -I${includedir}/itl` 对齐 |
| 11 | test_package 报 `fatal error: 'hijri.h' file not found`（在 `itl-gobject.h` 内） | 上游把 libitl 与 libitl-gobject 的头文件装在同一个 `$(includedir)/itl`，所以裸文件名能命中；Conan 下两者是各自独立的 prefix，libitl 的 `cpp_info` 只导出 `include`（头文件实际在 `include/itl/`） | 补丁 0004：公共头里改成 `#include <itl/hijri.h>` / `<itl/prayer.h>`。这样只用双方 `cpp_info` **已声明**的公共 include 目录即可解析（CMakeDeps 与 PkgConfigDeps 一致），无需往 cpp_info 里塞依赖包的绝对路径 |
| 12 | test_package 的 `test()` 报 `/data/storage/.../bash: Permission denied` | `CONFIG_SHELL` 在该环境下指向 Electron 自带、不可执行的 bash；`CONFIG_SHELL or which("bash") or ...` 链式取值会先命中它 | `_working_shell()` 改为**按实际执行探测**候选 shell（逐一 `bash -c "exit 0"`），避免 `os.access(X_OK)`（R49：HMDFS 上 chmod 被coerced，位测试恒假） |
| 13 | `make -j1` / test_package 的 CMake 编译在第一个编译目标上失败：日志从 libtool（或 cmake）回显的编译行**直接跳到** `*** [Makefile:483: libitl_gobject_la-itl-gobject.lo] Error 1`，**没有任何 clang 诊断**（`V=1`/`-v` 也不增加信息） | **OHOS 上编译器的 stdout/stderr 若是管道，编译会静默失败**。对照实验（同一配方、同一构建目录，唯一变量是输出去向）：`conan create > log` 稳定通过；由 python `capture_output=True`（管道）启动的 `conan create` 稳定失败；把 make 的输出改成 `> file` 后，库本体一次通过、失败点前移到 test_package 的 cmake 编译——把 test_package 的输出同样绑到文件后全绿。零延迟重试无效（重试仍是管道），说明起作用的是 fd 类型而非时机 | **让编译过程不接触管道**：①配方 `_make()` 在 OHOS 上把 `make` 的 stdout/stderr 重定向到 `build_folder/make-ohos.log`，跑完 `cat` 回显并保留退出码；②`test_package/conanfile.py` 的 `build()` 用 Conan 原生 API `cmake.configure/build(stdout=log, stderr=log)` 把 cmake 的两路输出绑到 `cmake-ohos.log` 再回显。两处都只影响 OHOS，日志一条不丢 |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| `patches/0001-src-Makefile.am.patch` | 删除硬编码的 Debian 系统路径 `-I/usr/include/itl`（两处：库 CFLAGS 与 introspection 的 gir CFLAGS），改由消费者 CPPFLAGS 提供包含目录 |
| `patches/0002-libitl-gobject.pc.in.patch` | `.pc` 的链接名 `-litl-gobject` → `-litl_gobject`（实际库文件是下划线） |
| `patches/0003-src-Makefile.am-vpath.patch` | 两条手写 glib-mkenums 规则补 `$(srcdir)/` 前缀，使 VPATH 构建成立 |
| `patches/0004-itl-gobject.h-include-prefix.patch` | 公共头 `#include <hijri.h>/#include <prayer.h>` → `#include <itl/hijri.h>/#include <itl/prayer.h>` |

补丁除 0001/0002 为可移植性修正外，0003/0004 都是「只用双方 cpp_info 声明的公共目录就能编译」的最小改动，不含任何 `#ifdef __OHOS__`。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| libitl | 0.8.0 | Hijri/Gregorian 转换、礼拜时间、Qibla（`AC_CHECK_LIB([itl],[getNorthQibla])`） |
| glib | 2.84.0.1 | `PKG_CHECK_MODULES(GOBJECT, gobject-2.0 >= 2.2.0)`；gobject/glib 头与库 |
| automake (tool) | 1.18 | 归档缺 Makefile.in，需要 automake 引导 |
| libtool (tool) | 2.5.4 | 归档缺 ltmain.sh，需要 libtoolize --install |

阶段一不构建 introspection：`configure.ac` 的 `GOBJECT_INTROSPECTION_CHECK([0.6.7])` 默认 `enable_introspection=auto`，配方再显式传 `--disable-introspection` 让结果确定；`HAVE_INTROSPECTION=false` 时 `src/Makefile.am` 的 gir/typelib 块整体跳过，不产出 `.gir`/`.typelib`。

## 验证结果

```bash
$ conan create archives/l/libitl-gobject/0.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 \
    --build=missing --build="libitl-gobject/*"
...
libitl-gobject/0.3: Package '967c23a4d143b7dfc7dfdcfde314e9d2a062aa05' created
======== Testing the package: Executing test ========
ok   - G2H(2026-07-28) == 1448-02-14 (got 1448-02-14)
ok   - H2G(G2H(2026-07-28)) round trips to 2026-07-28 (got 2026-07-28)
info - Qibla from Abu Dhabi: 99.886 deg
ok   - getPrayerTimes returns 6 entries (got 6)
ok   - prayer times are ordered Fajr..Isha (entry 5 hour 20 >= 18)
---
40 assertion(s), 0 failure(s)
test libitl-gobject 0.3: OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| `libitl_gobject.so` | 共享库（`libs = ["itl_gobject"]`，system_libs `m`） |
| `include/itl/itl-gobject.h` | 公共头（含 `itl-gobject-enums.h`） |
| 无 `.gir` / `.typelib` | 阶段一关闭 introspection |

## 注意事项

1. **ITL 转换函数的参数顺序与头文件命名不一致**（实测 libitl 0.8.0，重要）：
   `hijri.h` 里写的是 `G2H(sDate*, int yg, int mg, int dg)`，但实现按 **(day, month, year)** 取参——
   `G2H(&d, 28, 7, 2026)` → Hijri 1448-02-14（正确），`G2H(&d, 2026, 7, 28)` → 垃圾值或死循环。
   gtk-doc 注释里列的是 `@dg / @mg / @yg`，与实现一致，只有 C 形参名是错的。
   libitl-gobject 按位置原样转发，所以 `itl_G2H(28, 7, 2026)`、`itl_H2G(14, 2, 1448)` 才是正确用法；
   `itl_HijriGreg()` 也是按 (day, month, year) 转发。测试里的 golden 值都按这个契约写。
2. `G2H/H2G`（Umm al-Qura）与 `h_date/g_date`（表算法）结果会差 1–2 天，属上游算法差异，不要混用后做相等断言。
3. `itl_prayer_setLocation()` 的参数顺序是 **(longitude, latitude)**，不是常见的 (lat, lon)。
4. `getNorthQibla()` 返回的是 ITL 自己的约定：阿布扎比实测 99.886°，而大圆方位角（自北顺时针）约 260.1°，
   两者互补（360 − 260.1 = 99.9）。断言要按这个约定写。
5. **不要给依赖注入绝对路径的库文件到 LDFLAGS**（见问题 #6），否则 configure 的探针会带着外部 DT_NEEDED 进入运行期检查。
6. 上游 tag `0.3` 就是 master HEAD（`c6d96f1e`），归档与 Debian `orig.tar.gz` 内容一致，sha256 相同。
7. 后续可选项（阶段二）：引入 `gobject-introspection/1.78.1.1` 打开 `--enable-introspection`，产出 `Itl-1.0.gir` 与
   `libitl_gobject.typelib`，供 gjs/Python 绑定使用；本配方已把 `Itl_1_0_gir_CFLAGS` 的 Debian 路径一并清掉，阶段二无需再动补丁。
8. 配方与 test_package 都做了「输出绑文件」处理（见问题 #13），只为绕开 OHOS 上「编译器输出是管道就静默失败」这一平台行为；
   两处都保留完整日志（跑完 `cat` / `output.info` 回显），不会掩盖真实编译错误。若后续平台修复了该行为，这两处的重定向可以直接删掉。
---

**编译结束**: 2026-09-14 21:55
**最终状态**: built
