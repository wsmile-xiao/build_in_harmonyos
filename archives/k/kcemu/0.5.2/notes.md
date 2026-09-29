# kcemu 0.5.2 OHOS 适配记录

平台任务 `contrib-7771`，`kcemu 0.5.2`，`taskBranch=feat/kcemu-0.5.2`，路径 A。

## 源码

- kcemu：`https://deb.debian.org/debian/pool/contrib/k/kcemu/kcemu_0.5.2+dfsg.orig.tar.gz`
  sha256 `4fe1dad607ae3a1bfcab8808eec9932f169e58067631a3bdea642a5431d7c744`
- z80ex（硬依赖，制品仓无）：`https://deb.debian.org/debian/pool/main/z/z80ex/z80ex_1.1.21.orig.tar.gz`
  sha256 `6f5e521d068a614b41e10180ad4ae45b1bc258ec28c962543feb9078856c2530`

## 构建

1. **z80ex**：配方内 `clang -O2 -fPIC -fno-common -std=gnu99 -DWORDS_LITTLE_ENDIAN -DZ80EX_*` 编译
   `z80ex.c` / `z80ex_dasm.c` 为 `libz80ex.a` / `libz80ex_dasm.a`，头装到本地 prefix。
2. **autoreconf**：用真机 harmonybrew 的 autotools（不用 Conan 的 perl：其 XS 模块在本机加载报
   `Perl_newSVsv_flags: symbol not found`）。`autoreconf -fiv -I config -I config/m4`。
3. **E011 规避**：`sed -i 's/umask 077/umask 022/g' configure`（HMDFS 上 config.status 的
   `subs1.awk` 会因 umask 077 变成 Permission denied；E011 有记录）。
4. **configure**：`--host=aarch64-linux-gnu --with-debug-level=1 --disable-sound --disable-nls`
   + 禁用到全部可选编解码库（audiofile/sndfile/flac/vorbis/theora/xvidcore/dirac/schroedinger/
   avformat/gif/vncserver/mp3lame）。用 `--host=aarch64-linux-gnu` 而非 `*-ohos` 以免依赖
   config.sub 的 ohos 支持。
5. **make**：只构建非 GUI 目标 —— `libsys_unix.a`、`libdbg.a`、`libprefs.a`、
   `src/fileio`（kc2img/kc2tap/kc2wav/kc2raw）、`src/libdisk`（tdtodump）、`src/libtape`（kctape）、
   `test/kc/prefs`（t_prefs）。

## GTK+2 的替代方案（关键）

上游 `configure.ac:277` 有一句**无条件** `PKG_CHECK_MODULES(GTK, gtk+-2.0 >= 2.16.1)`，
找不到就 `AC_MSG_ERROR`。完整 gtk2 Conan 栈在本环境无法构建（`pango` 的 recipe 需要 meson，
制品仓只有 recipe 无二进制）。因此配方 `generate()` 里写一个 **stub `gtk+-2.0.pc`**：版本写成
2.24.33，Cflags/Libs 指向 **glib**（`-I<glib>/include/glib-2.0 -I<glib>/lib/glib-2.0/include`、
`-L<glib>/lib -lglib-2.0`）。这样 `GTK_CFLAGS`/`GTK_LIBS` 就等于 glib 的，configure 通过、
非 GUI 代码（prefs 需要 glib）也能编译链接。

## 补丁 / 桩

| 项 | 内容 |
|---|---|
| `patches/0001-configure-ac-config-headers.patch` | `AM_CONFIG_HEADER(include/kc/config.h)` → `AC_CONFIG_HEADERS([...])`（automake≥1.13 已移除旧宏） |
| `config/m4/sdl.m4`（配方运行时写入） | `AC_DEFUN([AM_PATH_SDL], [:])`——`--disable-sound` 时 autoconf 仍会展开该宏 |

## 上游测试

上游 `TESTS` 实际有 3 个（`t_prefs`、`t_memstream`、`t_load`），但 `configure.ac:271`
`AM_CONDITIONAL(HAVE_CPPUNIT, false)` 把后两个永久关掉。本配方只构建并实跑 `t_prefs`
（打印 `Preferences::save()` 正常结束）。运行需 `LD_LIBRARY_PATH` 指向 glib。

## 消费者测试

`test_package/test_kcemu.cpp`：链接安装后的 `libprefs.a`/`libdbg.a`/`libsys_unix.a` + glib，
调用 `Preferences::init/set_current_profile/find_profile/save`，4 项断言。工作目录经
`KCEMU_TEST_BASEDIR` 传入（prefs 的 `mkdirs` 只接受绝对路径）。

## 结果

- 真机 `conan create` 退出码 0；上游 t_prefs 通过、消费者 4/4。
- 产物：6 个 CLI 工具 + 3 个静态库 + 头文件。
- 未构建 GUI（GTK 栈不可用）与 X11 专用 `kcemu-remote`。
