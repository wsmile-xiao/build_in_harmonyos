# Cutter 1.2.6 测试框架 —— HarmonyOS PC (aarch64) 交叉编译记录

上游 libnfc 的 6 个单元测试用例依赖 Cutter 测试框架。Cutter 未随 OHOS SDK
提供，制品仓亦无对应包（制品仓 `cutter/1.04` 是**同名不同物**的 TCP/IP
连接切断工具，非 C 单元测试框架）。本文件记录本机交叉编译 Cutter 的完整方法与踩坑。

## 0. 环境

| 项 | 值 |
|----|----|
| 目标平台 | HarmonyOS PC / OpenHarmony 6.0，aarch64（musl） |
| 编译器 | OHOS SDK clang 15.0.4（`Target: aarch64-unknown-linux-ohos`） |
| Cutter 版本 | 1.2.6 |
| GLib | `glib/2.84.0`（ohpcd 制品仓已发布，OHOS armv8，shared） |

## 1. 源码获取

Cutter 由 SourceForge 托管。**GitHub 镜像 `clear-code/cutter` 不携带
预生成的 `configure`**，而本机无 `automake` / `libtool` / `aclocal`，
无法 `autoreconf`。因此必须取 SourceForge 的 release tarball（自带
`configure` / `aclocal.m4` / `config/ltmain.sh`）：

```sh
curl -sL -o cutter-1.2.6.tar.gz \
  "https://sourceforge.net/projects/cutter/files/cutter/1.2.6/cutter-1.2.6.tar.gz/download"
tar xzf cutter-1.2.6.tar.gz
```

## 2. 三元组补丁：让 autotools 认识 linux-ohos

cutter 自带的 `config.sub`（2016-11-04）支持 `aarch64` 但**不认识 `ohos`**，
`config.guess` 亦无法识别 HarmonyOS：

```
$ sh config/config.sub aarch64-linux-ohos
Invalid configuration `aarch64-linux-ohos': system `ohos' not recognized
```

处理方式与 libnfc 配方一致（见 `archives/l/libnfc/1.8.0/patches/0001·0002`），
在本机对源码树的 `config/config.sub` / `config/config.guess` 就地补丁：

- `config.sub`
  1. `maybe_os` 分支列表加入 `linux-ohos*`
  2. 在 `android-linux)` 分支后新增 `linux-ohos | *-linux-ohos)` 分支
  3. OS 白名单加入 `-linux-ohos*`
- `config.guess`：`case "${UNAME_MACHINE}:${UNAME_SYSTEM}:..." in` 首部新增
  `*:HarmonyOS:*:*)` 分支，输出 `${MACHINE}-unknown-linux-ohos`

补丁后：

```
$ sh config/config.sub aarch64-linux-ohos
aarch64-unknown-linux-ohos
```

## 3. pkg-config 重定位 GLib

ohpcd 的 glib 包 `.pc` 采用 root-prefix（`prefix=/`），直接用会得到
`-I/include/...` 这类错误路径。两种手段组合解决：

1. **sysroot 前缀**：`PKG_CONFIG_SYSROOT_DIR=<glib 包根>`，把 `.pc` 中所有
   `-I/-L` 的 `/xxx` 重写为 `<glib 包根>/xxx`
2. **剥离私有依赖**：`glib-2.0.pc` 的 `Requires.private: libpcre2-8`、
   `gobject-2.0.pc` 的 `Requires.private: libffi` 在 `--cflags` 时会被强制
   解析而报错。glib 为 shared 且已把 pcre2/ffi 静态编入（
   `readelf -d libglib-2.0.so.0` 仅 `NEEDED libintl.so.8` / `libc.so`），
   故把 `.pc` 复制到独立目录并删除 `Requires.private:` 行即可
3. **代码生成工具路径**：`glib-2.0.pc` 的 `glib_mkenums=${bindir}/glib-mkenums`
   会解析成 `/bin/glib-mkenums`（不存在）。把 `.pc` 中
   `bindir=${prefix}/bin` 改写为 glib 包的绝对 `<glib>/bin`，使
   `glib-mkenums` / `glib-genmarshal` 正确定位

所需工具链程序（`glib-mkenums` 等）本身是 Python 脚本，运行时需要 `python3`
在 PATH 中。

## 4. configure：中和 intltool/gettext 检查

cutter 的 `configure` 无条件执行 `AM_GLIB_GNU_GETTEXT` / intltool 检查，
即使 `--disable-nls` 也要求 `intltool-update` / `msgmerge` / `perl XML::Parser`
全部就位。本机只有 stubs，故：

- PATH 前置 stub 目录，提供 `intltool-update`（输出 `(intltool) 0.51.0`）、
  `intltool-merge`、`intltool-extract`、`msgmerge`、`msgcat`、`msgunfmt`
- 就地修补 `configure`：把 intltool/gettext 相关的 8 处
  `as_fn_error $? "..." "$LINENO" 5` 中和为 `:`，并令
  `INTLTOOL_APPLIED_VERSION=0.51.0`

因本次不构建 `po/` 子目录，NLS 相关工具实际不被调用，中和是安全的。

## 5. 构建顺序与模块

install 需要在构建时给出完整依赖顺序，`cutter/` 链接依赖 `gcutter/`：

```
m4macros → glib-compatible → gcutter → cutter
```

运行 Cutter runner 还需要 report / stream / UI 模块：

```
module/ui                (console.so)          ← 默认 UI
module/factory/ui        (console_factory.so)
module/report            (xml.so)
module/factory/report    (xml_factory.so)
module/stream            (xml.so)
module/factory/stream    (xml_factory.so)
```

### 5.1 上游构建缺陷：`xml_la_CPPFLAGS =` 覆盖 `AM_CPPFLAGS`

`module/report/Makefile.am` 中：

```make
AM_CPPFLAGS = -I$(top_builddir) -I$(top_srcdir)
...
xml_la_CPPFLAGS =
xml_factory_la_CPPFLAGS =
```

automake 语义下，per-target 的 `*_CPPFLAGS`（即使为空）会**替换** `AM_CPPFLAGS`，
导致 VPATH 构建时 `#include <cutter/cut-module-impl.h>` 找不到头文件。
绕过方式是在 make 命令行显式回填：

```sh
make -C module/report \
  xml_la_CPPFLAGS="-I$BUILD -I$SRC" \
  xml_factory_la_CPPFLAGS="-I$BUILD -I$SRC"
```

（`module/loader-customizer` 依赖 `cppcutter/libcppcutter.la`，与本任务无关，可跳过。）

## 6. ⚠️ 运行期关键坑：musl 加载器不识别 soname 符号链接

按惯例把 libtool 产物整目录复制到 RUNPATH 目录后，`cutter` 仍报：

```
Error loading shared library libcutter.so.0: (needed by .../.libs/cutter)
Error relocating ...: cut_init: symbol not found
```

而**同一目录下用 ctypes `dlopen` 该 `.so` 却成功** —— 排除库本身问题。
进一步用最小工程验证 RUNPATH 与 `LD_LIBRARY_PATH` 机制均正常，
最终定位：**需把 `libcutter.so.0` 由指向 `libcutter.so.0.1.0` 的符号链接
替换为实体文件**，加载即成功：

```sh
cp -f <prefix>/lib/libcutter.so.0.1.0 <prefix>/lib/libcutter.so.0
```

同样处理 `libusb-1.0.so.0`。

## 7. 模块目录与运行

模块目录编译进 `libcutter`（`${libdir}/cutter/module`），亦可用环境变量
`CUT_FACTORY_MODULE_DIR` 覆盖。按第 5 节的层级放置模块后：

```sh
cd <testmod>
<cutter-build>/build6/cutter/cutter <testmod>
```

Cutter 会扫描目录内的测试模块，逐个加载并执行其中的 `test_*` 函数。

## 8. 交叉编译要点小结

| # | 问题 | 根因 | 处理 |
|---|------|------|------|
| 1 | GitHub 源码树无 `configure` | 本机缺 automake/libtool | 改用 SourceForge release tarball |
| 2 | `system 'ohos' not recognized` | 2016 版 config.sub 无 ohos | 补 config.sub / config.guess（复用 libnfc 补丁思路） |
| 3 | `Package libpcre2-8/libffi not found` | `.pc` 的 `Requires.private` 被 `--cflags` 强制解析 | 删除 `Requires.private:` 行（shared glib 已静态编入） |
| 4 | `//bin/glib-mkenums: not found` | `.pc` root-prefix 导致 bindir=`/bin` | `.pc` 中 bindir 改写为 glib 绝对路径 |
| 5 | `intltool is too old` / `XML::Parser required` | `--disable-nls` 仍执行 intltool 检查 | PATH stub + 中和 configure 中 8 处致命检查 |
| 6 | `No rule to make target '../gcutter/libgcutter.la'` | libcutter 链接依赖 gcutter | 按 m4macros→glib-compatible→gcutter→cutter 顺序构建 |
| 7 | `xml_la_CPPFLAGS =` 空值覆盖 `AM_CPPFLAGS` | 上游 automake 写法缺陷 | make 命令行回填 `*_CPPFLAGS` |
| 8 | 运行期 `Error loading shared library libcutter.so.0`（reason 为空） | musl 加载器无法通过 soname 符号链接定位 | 用实体文件替换 soname 符号链接 |
| 9 | `env: exec python3: No such file or directory` | `glib-mkenums` 是 Python 脚本 | PATH 中加入 python3 |
