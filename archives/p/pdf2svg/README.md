# pdf2svg

## 简介

pdf2svg 是一个把 PDF 页面渲染成 SVG 的命令行工具：它用 Poppler 解析并光栅化
PDF 页面内容，再交给 Cairo 的 SVG 后端输出矢量图形。相比 `pdftocairo` 这类
"PDF → 位图"的路径，它的产物是**矢量** SVG，因此文本/线条在放大后仍然清晰。

- 上游: https://github.com/dawbarton/pdf2svg
- 许可证: GPL-2.0-or-later
- 平台: OpenHarmony PC (aarch64-unknown-linux-ohos), musl, clang 15
- 构建: autotools（tarball 自带 configure / Makefile.in）
- 包类型: application（产物只有 `bin/pdf2svg`，无可链接库、无可 include 头）

## 功能概述

```
pdf2svg <input.pdf> <output.svg> [<pdf page number or 'all'>]
```

- **单页转换**：不给页号时默认渲染第 1 页。
- **整本转换**：页号传 `all` 时，输出参数被当作 **printf 格式串**使用
  （例如 `page-%d.svg`），逐页展开成多份文件。
- **退出码约定**：`pdf2svg.c` 的返回值是负值取低 8 位 ——
  `-2` → 254（用法错误）、`-3` → 253（输入打不开）、
  `-4` → 252（转换失败，含页标签不存在）、`-5` → 251（页数超限）。
- 没有 `--version` / `-V` 选项，程序不打印版本号。

## OHOS 适配要点（0.2.4）

1. **不调用 pkg-config。** 上游 `configure.ac` 用
   `PKG_CHECK_MODULES(CAIRO, cairo >= 1.16)` 与
   `PKG_CHECK_MODULES(POPPLERGLIB, poppler-glib >= 0.5.4)` 声明依赖。
   制品仓里各依赖包**自带的 `.pc` 记录了构建机前缀**（`cairo.pc` 的
   `prefix=/`；`poppler-glib.pc` 指向另一台构建机的 `.conan2` hash 目录；
   `glib-2.0.pc` 的 `prefix=/` 且 `Libs` 含 `-lintl`），把它们放进
   `PKG_CONFIG_PATH` 会让 pkg-config **静默成功**却给出错误路径。
   配方改走 `AC_ARG_VAR` 逃生口：`CAIRO_CFLAGS` / `CAIRO_LIBS` /
   `POPPLERGLIB_CFLAGS` / `POPPLERGLIB_LIBS` 四个变量非空即直接采用，
   由 `cpp_info.aggregated_components()` 现算 `-I` / `-L` / `-l`。
2. **`-I` 必须按组件聚合。** glib 的 `include/glib-2.0`、`lib/glib-2.0/include`
   （`glibconfig.h`）与 `include/gio-unix-2.0` 只存在于 `cpp_info` 的**组件**里，
   根 `cpp_info.includedirs` 只有一层 `include`，用它拼 CFLAGS 会让
   `#include <glib.h>` 失败。
3. **只链 `-lpoppler-glib`。** poppler 的根级 `cpp_info.libs` 是
   `['poppler','poppler-glib','poppler-cpp']` 的并集，照抄会白白拖进
   `poppler-cpp`；pdf2svg.c 只 include `<poppler.h>` / `<poppler-document.h>` /
   `<poppler-page.h>`。
4. **out-of-source 构建**：conan 的 `Autotools.configure()` 不会自己 `chdir`，
   配方在 `build()` 里显式切到 `build_folder`。
5. **平台修补（只改生成的 `configure`，不改源码）**：
   `umask 077` → `umask 022`（HMDFS 下 077 建出的临时目录不可写，E002/E114）；
   `ac_pwd=\`pwd\`` 加兜底（HMFS `getcwd` 不可达，HMBS `[shell_getcwd]`），
   配合预置的 `PWD`。
6. **运行期寻库**：OHOS loader 可能忽略 `LD_LIBRARY_PATH`
   （HMBS `[stale_runtime_library]`），test_package 从 `bin/pdf2svg` 的
   `DT_NEEDED` 出发做 BFS，把闭包内 `.so` 的绝对路径经 `LD_PRELOAD` 注入。

版本号说明：tarball 的 tag 是 **v0.2.4**，而上游 `configure.ac` 的
`AC_INIT(pdf2svg, 0.2.1, ...)` 从未随发布递增；Conan 包版本按 tag 记为 `0.2.4`。

## 依赖关系

- **编译期（直接 requires）**：`poppler/25.12.0.2`（transitive_headers +
  transitive_libs）、`cairo/1.18.4`（同）、`glib/2.84.0.1`（transitive_headers）、
  `fontconfig/2.18.1.1`（`override=True`，消解 poppler 钉 2.18.1 与 cairo 钉
  2.18.1.1 的 version conflict）
- **运行期闭包**：host 依赖共 15 个（boost、expat、freetype、lcms2、
  libjpeg-turbo、libpng、libtiff、libwebp、openjpeg、pixman、zstd 等）

## 测试

上游 **无**自动化测试套件（tarball 无 `tests/` 目录，`Makefile.am` 只有
`bin_PROGRAMS = pdf2svg`，无 `meson.build` / `CMakeLists.txt`），因此 `build()`
不跑 `make check`。被测行为由 `test_package/test_pdf2svg.sh` 对**已安装的**
`bin/pdf2svg` 做 6 项端到端断言：用法输出 → 单页转换 → `all` 多页转换 →
输入打不开 → 页标签不存在 → 两页渲染结果不同。

版本索引见 `manifest.yaml`；命令行工具声明见 `commands.json`（R38）。

## 参考资料

- 上游仓库: https://github.com/dawbarton/pdf2svg
- Poppler: https://poppler.freedesktop.org/
- Cairo: https://www.cairographics.org/
