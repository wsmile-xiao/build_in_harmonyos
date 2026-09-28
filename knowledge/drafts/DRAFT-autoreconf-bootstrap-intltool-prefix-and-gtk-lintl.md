# DRAFT-autoreconf-bootstrap-intltool-prefix-and-gtk-lintl（草稿）

- **软件**：l3afpad 0.8.18.1.11（https://github.com/stevenhoneyman/l3afpad，Leafpad 的 GTK3 分支）
- **构建系统**：autotools（GitHub git archive 交付，**无 configure**，需 `autoreconf -fi` 引导）
- **平台**：HarmonyOS PC / aarch64，`clang 15.0.4`，GTK+3 3.24.43
- **状态**：DRAFT

## 现象（依次踩到四坑）

```
Can't locate Automake/Config.pm in @INC ... at /storage/Users/currentUser/usr/local/bin/aclocal line 34
autoreconf: error: aclocal failed with exit status: 2

configure.ac:6: error: possibly undefined macro: AC_PROG_INTLTOOL
configure.ac:47: error: possibly undefined macro: AM_GLIB_DEFINE_LOCALEDIR

grep: //share/aclocal/intltool.m4: No such file or directory
cp: bad '//share/intltool/Makefile.in.in': No such file or directory
intltoolize: cannot copy '//share/intltool/Makefile.in.in' to 'po/Makefile.in.in'

configure: error: GNU gettext tools not found; required for intltool

ld.lld: error: undefined symbol: g_libintl_gettext
configure: error: C compiler cannot create executables     # 修 -lintl 时引入的次生问题
```

## 根因与解法

### 1. 设备 automake 不可用，且遮蔽 tool_requires

设备自带 `automake` 1.17 驱动配 1.16 的 share 目录 → `Can't locate
Automake/Config.pm`。而 `/usr/local/bin` 在 PATH 里**优先于** tool_requires
的 bin 目录，`self.run(env=[...])` 的 PATH 又是追加式，竞争不过它。

**解法**：`tool_requires("automake/1.18")` + `libtool` + `intltool` + `gettext`，
并以 `env="conanbuild"` 运行 `autoreconf`——该虚拟环境导出 `ACLOCAL` /
`AUTOMAKE` / `LIBTOOLIZE` / `_lt_pkgdatadir` / `PERL5LIB`，直接指向正确副本。

### 2. `intltoolize` 硬编码 `prefix=/`

`intltoolize` 里 `prefix=/` 是常量，只有 MINGW32 分支才从 `$0` 推导；`autoreconf`
按裸名调用它（`$0 == "intltoolize"`），于是它去 `//share/intltool` 找数据 →
`cannot copy '//share/intltool/Makefile.in.in'`。

PATH wrapper、绝对路径 exec **都无效**。**唯一解法**：复制脚本，把首处
`^prefix=/` 改写成 intltool 包的 package_folder，放到 `<build>/toolshim/`，
再以 `PATH="<toolshim>:$PATH"` 前置。

### 3. aclocal 宏缺失

`AC_PROG_INTLTOOL`（intltool.m4）与 `AM_GLIB_DEFINE_LOCALEDIR`（glib 的
`glib-gettext.m4`）需显式传入：`autoreconf -fi -I<依赖 aclocal 目录>...`。
注意 autoconf 2.72 对缺失宏只报 `possibly undefined macro` **警告**，但生成
的 configure 后续会失败——必须真正喂给 aclocal。同时把宏暂存到源码树 `m4/`
作双保险。

另外 intltool 的 configure 硬检查 GNU gettext 工具 → 需
`tool_requires("gettext/0.22.5.1")`。

### 4. glib 的 `g_libintl_*` 别名

glib 的 `gi18n.h` 把 `gettext()` 映射到 `g_libintl_*` 别名，**只有 glib 包内
`libintl.a` 导出**，而其生成的 `.pc` 不列 `-lintl`。

**踩坑**：把 `-lintl` 放进 configure 的 `LIBS` 会让 `AC_PROG_CC` 的 conftest
链接失败：

```
configure: error: C compiler cannot create executables
```

**正确做法**：在 **make 阶段**传 `LIBS="..."`，且整体加引号（不加引号时 make
会把 `-L<dir>` 当成命令选项并打印 usage 而后失败）。

```python
autotools.make(args=["-j1", 'LIBS="%s"' % self._intl_link_flags()])
```

## 验证

`conan create archives/l/l3afpad/0.8.18.1.11`（ohos-aarch64）通过，test_package
5 项断言：`aarch64 ELF verified`、GTK+3 全闭包（gtk3/gdk3/pango/cairo/gdk-pixbuf/
harfbuzz/freetype/fontconfig/png/jpeg/tiff/webp… 20+ 库）解析成功、
`GTK+3 closure resolved; stopped at display init as expected`。

> 补充观察：l3afpad 的 `parse_args()` 用 `gtk_get_option_group(TRUE)` 构造
> GOptionContext，**解析选项时就会打开显示**——设备实测连 `--version` 也输出
> `l3afpad: Cannot open display:` 并以 255 退出。因此无显示环境下的消费者测试
> 只能断言"链接闭包可解析 + 停在显示初始化"。

## 相关

- `archives/l/l3afpad/0.8.18.1.11/conanfile.py`
- `archives/a/abiword-plugin-docbook/3.0.8/conanfile.py`（tool_requires + VirtualBuildEnv 先例）
- `archives/g/goffice/0.10.57.1/conanfile.py`（intltool / PKG_CONFIG_PATH 先例）
- `archives/a/acedb/4.9.39+dfsg.02/conanfile.py`（`g_libintl_*` 代理先例）
- `knowledge/drafts/DRAFT-old-autotools-config-guess-sub-ohos-and-musl-pthread-cancel.kv`
