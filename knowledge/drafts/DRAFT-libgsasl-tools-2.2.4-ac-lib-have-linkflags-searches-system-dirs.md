# DRAFT: AC_LIB_HAVE_LINKFLAGS 探测的是系统目录与 LD_LIBRARY_PATH，不是 pkg-config —— 交叉构建下会被 /usr/local 静默满足

> Contributor: username- | Status: DRAFT | Created: 2026-09-17
> 来源: libgsasl-tools 2.2.4 适配（`gsasl` 程序；GNU SASL 用该宏探测 GnuTLS 与 GNU libidn）

## 症状

上游 `configure.ac` 里两个可选依赖是这么探测的：

```m4
AC_ARG_WITH(gnutls, ..., gnutls=$withval, gnutls=yes)
if test "$gnutls" != "no"; then
  AC_LIB_HAVE_LINKFLAGS(gnutls,, [#include <gnutls/gnutls.h>],
    [gnutls_session_set_verify_cert (NULL, NULL, 0);])
fi
...
AC_ARG_WITH(stringprep, ..., stringprep=$withval, stringprep=yes)
if test "$stringprep" != "no"; then
  AC_LIB_HAVE_LINKFLAGS(idn,, [#include <stringprep.h>],
    [stringprep_check_version (0);])
fi
```

交叉构建到 OHOS 时 `configure` 一声不响地把探测**判为成功**：

```
checking for libgnutls... yes
checking if STARTTLS support via GnuTLS should be built... yes
```

但本仓库里既没有 `gnutls` 配方也没有 `libidn` 配方，制品仓里同样没有。
链接行于是被塞进 `-L/usr/local/lib -lgnutls`，产物带上一个**没有任何包负责交付**的
`DT_NEEDED libgnutls.so.*`：构建全绿，真机上要么加载期失败，要么撞上设备里那份
版本完全不同的 `/usr/local` 副本。

## 根因

`AC_LIB_HAVE_LINKFLAGS` 是 gnulib 的宏（`m4/lib-link.m4`），它不是 pkg-config 封装，
而是**直接遍历系统库搜索路径**：

1. 先看 `$LDFLAGS` / `$LIBS` 里已经有的 `-L`；
2. 再看 **`LD_LIBRARY_PATH`**；
3. 最后看**编译器默认的系统目录**（`/usr/local/lib`、`/usr/lib` …）。

它既不知道 conan 的 `requires()`，也不认 `PKG_CONFIG_PATH`。所以
"已经 `self.requires()` 了" ≠ "它找得到"，反过来更要命：
**"根本没人提供这个库" ≠ "它找不到"** —— 只要构建机前缀里有同名 `.so`/`.a`，
探测就会成功，链接行就被污染。

这与 `libheif-tools` 里 `CMAKE_DISABLE_FIND_PACKAGE_<name>` 是同一类问题
（系统前缀里的第三方包配置对 hermetic 交叉构建是负面因素），只是落在
autotools 的 `AC_LIB_HAVE_LINKFLAGS` 上。

## 判据

一条命令列出所有会去系统目录找库的探测：

```sh
grep -n 'AC_LIB_HAVE_LINKFLAGS\|AC_CHECK_LIB\|AC_SEARCH_LIBS' configure.ac
```

再看 `configure` 的实际判定（在鸿蒙 worker 上跑 `conan create`，看这一节）：

```sh
grep -nE 'checking for lib(gnutls|idn)\.\.\.|STARTTLS support|non-ASCII support' <build>/conan-create.log
```

若这里出现 `yes`，而依赖清单里并没有对应配方，就是命中本条目。
交叉构建时还可以直接看链接行：

```sh
grep -nE '\-lgnutls|\-lidn|/usr/local/lib' <build>/conan-create.log
```

## 修复

**1) 显式关掉所有"系统前缀能满足、但没有配方"的探测**（首选）：

```python
tc.configure_args += [
    "--without-gnutls",     # STARTTLS 支持关闭
    "--without-stringprep", # 非 ASCII / IDN 支持关闭
]
```

代价是要在 `notes.md` 里写清楚功能裁剪：GnuTLS 关掉后 `gsasl --starttls` 不可用，
libidn 关掉后非 ASCII 用户名不参与 stringprep 规范化。

**2) 如果功能必须保留**，就把依赖真正做成配方并让链接行只指向它，
而不是靠系统目录碰运气（在 `tc.extra_cflags/extra_ldflags` 里前置
`-I<dep>/include -L<dep>/lib`，并用 `PKG_CONFIG_PATH` 指向 conan 的 `.pc`）。

## 同一次适配里的另外两个点

### `bin_PROGRAMS = gsasl` 就是整个 tools 面

`src/Makefile.am` 只有一行 `bin_PROGRAMS = gsasl`；`examples/` 里的
`client` / `client-serverfirst` / `client-mech` / `smtp-server` 全是
`noinst_PROGRAMS`，**不安装**。所以拆 tools 包时不存在的"要不要带示例程序"
问题，答案是不带；`make -C src install-exec DESTDIR=<pkg>` 一键完成，
`lib/` `include/` `share/` 再防御性删掉。

### gengetopt 生成物把 `Makefile.am` 写进了依赖

```make
gsasl_cmd%c gsasl_cmd%h: gsasl.ggo Makefile.am
	$(AM_V_GEN)gengetopt --unamed-opts="HOST [PORT]" \
		--no-handle-version --no-handle-help \
		--input $< --file-name gsasl_cmd
```

发行 tarball 里所有文件时间戳相同（本包为 `2026-06-16 05:36:52`），
所以默认不会触发重生成；**但只要打任何触碰 `src/Makefile.am` 或
`src/gsasl.ggo` 的补丁，`make` 就会去调 worker 上根本不存在的 `gengetopt`**。
判断方式：

```sh
ls -l --time-style=+%F src/gsasl.ggo src/gsasl_cmd.c src/Makefile.am
command -v gengetopt      # worker 上没有
```

结论：能被 `build-aux` 补丁解决的平台问题就不要碰 `src/Makefile.am`；
非碰不可时，要么同时把生成物的时间戳调新（`touch`），要么把 `gengetopt`
作为 `tool_requires` 引进来。