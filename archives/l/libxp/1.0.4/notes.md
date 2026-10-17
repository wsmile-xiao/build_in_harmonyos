# libXp 1.0.4 适配笔记

## 编译环境
- 构建系统: autotools（官方 tarball 自带预生成 configure / Makefile.in，无需 autoreconf）
- 编译日期: 2026-09-20
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- Conan 包: `libxp/1.0.4`，产物 `libXp.so.6.2.0`（`src/Makefile.am` 的 `XP_VERSION=-version-number 6:2:0`）
- 状态: built

> 注意：libXp 1.0.4 **自己不带也不装头文件**（见「问题 8」），下面列出的
> 头文件全部来自依赖包，经 `cpp_info.requires` 传递到消费者。

## 依赖
- `libx11/6.4.0`（制品仓已发布，提供 Xlib.h / Xlibint.h / Xlocale.h / Xutil.h 与 x11.pc）
- `libxext/6.4.0.1`（提供 `X11/extensions/extutil.h` 与 libXext 的 Xext* 符号）
- `libxau/1.0.11`（提供 `X11/Xauth.h` 与 XauReadAuth/XauFileName/XauDisposeAuth）
- `xorgproto/2025.1`（提供 `X11/extensions/Print.h`、`Printstr.h` 与 Xatom.h/Xos.h/Xfuncproto.h）

上游 `PKG_CHECK_MODULES(XPRINT, [x11 >= 1.6] xext xextproto xau printproto)` 里的
**xextproto / printproto 都不是 Conan 包**：xextproto 随 xorgproto 一起发布但
xorgproto/2025.1 只带 `include/`（无 `.pc`），printproto 更是全生态都不再有
`printproto.pc`。配方不依赖 pkg-config 求解这条依赖。

## 编译步骤

```bash
conan create archives/l/libxp/1.0.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `Package printproto was not found` / `The pkg-config script could not be found ... printproto` | `PKG_CHECK_MODULES(XPRINT, [x11 >= 1.6] xext xextproto xau printproto)` 要求 `printproto.pc`；printproto 自 X.Org 7.7 并入 xorgproto 后**没有任何包**再提供它（xorgproto/2025.1 的 `share/pkgconfig` 下 29 个模块 .pc 里没有）；且 CI worker 上根本没有 pkg-config 可执行文件 | 用 PKG_CHECK_MODULES 的 **AC_ARG_VAR 逃生口**：把 `XPRINT_CFLAGS`/`XPRINT_LIBS` 设成非空，configure 的 `if test -n "$XPRINT_CFLAGS"` 直接命中，`pkg_cv_*` 不取 pkg-config 也不会置 `pkg_failed`。两个变量由 `_dependency_dirs()` 从 Conan 依赖目录算出（同 libxtst/1.2.5 的 XEXT_CFLAGS/XEXT_LIBS） |
| 2 | libtool 链接 `-lXau` 报 `cannot find the library '.../libXau.so'` 或 `is not a valid libtool archive` | 发布的 `libxau/1.0.11` 里 `libXau.la` 的 `libdir=` 是构建机临时目录（`/storage/Users/currentUser/.conan2/p/b/libx<hash>/p/lib`），本机/CI 上不存在 | `_relocate_dep_la_files()` 在 configure 前把依赖 `.la` 的 `libdir=` 就地改写为当前 package 的 `lib` 目录 |
| 3 | 链接行里混入 `/storage/Users/currentUser/usr/local/lib`（CI worker 残留的静态 glib 目录） | `libXau.la` 的 `dependency_libs=' -L/storage/Users/currentUser/usr/local/lib'`，libtool 会把它带进链接行 | 同上，一并把 `dependency_libs=` 清空（本构建用显式 `-L`/`-l` 给出全部依赖） |
| 4 | `./confXXXX/subs1.awk: Permission denied`（configure 生成 config.status 时） | HMDFS 上 `umask 077` 建出来的临时子目录不可执行（E002） | configure 中 `umask 077` → `umask 022`（该版本共 2 处） |
| 5 | configure 的 shebang `#! /bin/sh` 在 OHOS 上不可用 | OHOS 的 `/bin/sh` 与 CI worker 实际 shell 路径不同 | `_patch_configure_runtime_shell()` 把 shebang 换成 `_ohos_shell()` 探到的实际 shell（同 libxext / libxtst） |
| 6 | `Invalid configuration 'aarch64-unknown-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'` | libXp 1.0.4（2010）自带的 config.guess/config.sub 不认识 linux-ohos | 不打 config.sub 补丁，改用 `tc.update_configure_args({"--build"/"--host": "aarch64-unknown-linux-gnu"})`（libxext/6.4.0.1 同款）；编译器仍来自 Conan profile |
| 7 | 安装出来的 `xp.pc` 带 `Requires: printproto`，任何消费者 `pkg-config --cflags xp` 直接失败 | 上游 `xp.pc.in` 写死 `Requires: printproto`；`Requires.private: x11 xext xau` 是对的，公开的那条不是 | `package()` 里改写为 `Requires: x11 xext`（都是实际存在的模块），并把 prefix/libdir/includedir 改成可重定位形式 |
| 8 | 消费者 `find_package(libxp)` 在 CMake **generate** 阶段失败：`Imported target "libxp::libxp" includes non-existent path "/…/p/b/libxp<hash>/p/include" in its INTERFACE_INCLUDE_DIRECTORIES`（CI #53038） | libXp 1.0.4 **自身不安装任何头文件**：上游 `SUBDIRS` 只有 `src` 和 `man`，`make install` 只落地 `lib/libXp.so*`、`share/man/man3/*.3`、`lib/pkgconfig/xp.pc`，package_folder 下不存在 `include/`；而 `cpp_info.includedirs` 默认是 `["include"]` | `package_info()` 里显式 `self.cpp_info.includedirs = []`。头文件全部由依赖提供并经 `cpp_info.requires` 传递：`X11/extensions/Print.h`、`Printstr.h`、`Xatom.h`、`Xos.h`、`Xfuncproto.h` ← xorgproto/2025.1；`X11/Xauth.h` ← libxau；`X11/extensions/extutil.h` ← libxext；`X11/Xlib.h` ← libx11 |
| 9 | 消费者测试链接报 `ld.lld: error: undefined symbol: Xmalloc`（CI #53439；编译期另有一条 `call to undeclared function 'Xmalloc'` 警告） | 测试里的自定义 hinter 照抄 libXp 源码用 `Xmalloc()` 分配返回值，但 `Xmalloc` 声明在 libX11 的**私有头** `<X11/Xlibint.h>`、由 libX11 导出；消费者链接行上只有 `-lXp`，而 lld 默认不顺着 `libXp.so` 的 DT_NEEDED 去间接依赖里找符号 | 测试改用 `malloc()` + `<stdlib.h>`。这是**等价且更正确**的写法：hinter 返回串由 libXp 自己 `XFree()` 释放（`XpLocale.c:242/251`），而 `XFree` 最终就是 `free()`，分配器配对不变；测试不再依赖库的私有符号 |

## 源码修改

无。本适配**不修改上游任何源文件**：上述修复全部发生在
① 生成的 `configure`（umask / shebang）、② 依赖包发布的 `.la`、
③ 安装出来的 `xp.pc` 三类**构建产物**上，配方内完成，`patches/` 为空。

## 上游测试

`make check` 是**空目标**：`Makefile.am`、`src/Makefile.am`、`man/Makefile.am`
三处都没有 `check_PROGRAMS`、`TESTS`、`check-local`，release tarball 里也没有
任何测试源码（`src/` 下只有 16 个 `.c` + `XpExtUtil.h`）。故 `build()` 内不跑
上游测试，消费者侧断言全部在 `test_package/test_libxp.c`。

## 验证结果

本机（Windows x86_64）没有 aarch64-ohos 运行环境，构建与测试全部由 CI
流水线在 OHOS worker 上执行 `conan create ... --build=missing` 完成，
以 PR 的 CI-BOT 结论为准。本机做的是静态自检：`conanfile.py` /
`test_package/conanfile.py` 的 AST 语法检查、`conandata.yml` /
`manifest.yaml` / `test_package/MANIFEST.yml` 的 YAML 解析、四个依赖的
`conan list -r ohpcd` 命中核对，以及上游 tarball 的 `make check` 空目标核对。

`test_package/test_libxp.c` 在有图/无图环境下都输出同一行：

```
libxp consumer checks: 13/13 passed
```

场景一 默认 hinter（4 条）／场景二 `%locale%` 关键字替换（5 条）／
场景三 描述优先（1 条）／场景四 鸿蒙特有：musl 拒绝的 locale 不得被当成
生效值上报（3 条）。全部走 libXp 里唯一一族不需要 X server 的公开接口，
可在无图形服务的 worker 上真实执行。

场景四的断言数与运行环境无关：无论 `setlocale("en_US.UTF-8")` 被接受与否
都固定 3 条（`net != NULL`、`net == 实际生效 locale`、
`(被接受) == (net == 请求值)`），故总数恒为 13。
