# Img (libtk-img)

> Tcl/Tk 图像格式扩展 —— 以 `package require Img` 为 Tcl/Tk 增加多种图像格式的读写能力。

## 简介

Img（上游工程名 **TkImg**，发行包名 `Img-<ver>.tar.gz`，Conan 包名 `libtk-img`）是 Tcl/Tk 的
图像格式扩展。加载后通过 `package require Img` 注册一批 `image create photo` 的**格式处理器**
（format handler），使 Tcl/Tk 能读写 BMP / GIF / ICO / JPEG / PCX / PIXMAP / PNG / PPM / PS /
SGI / SUN / TGA / TIFF / WINDOW / XBM / XPM / DTED / RAW / FLIR 等格式（PDF 需 Ghostscript，
经 `ps` 处理器读取）。

它的构建系统是 TEA（Tcl Extension Architecture）：顶层 `configure.ac` 通过
`TEA_CONFIG_SUBDIR` 声明 24 个子目录，每个子目录各自生成一个 Tcl 可 `load` 的动态库。
包内 `compat/` 自带 zlib / libpng / libtiff / libjpeg 源码随包编译并静态并入各处理器，
因此外部依赖只有 tcl / tk 与 X11 一族。

## OHOS 适配要点

- **uname shim**：OHOS 上 `uname -s` 返回 `HarmonyOS`，内嵌的 `compat/libtiff`、`compat/libjpeg`
  自带 `config.guess` 不识别 → `configure: error: cannot guess build type`，进而
  `tif_config.h` / `tiffconf.h` / `jconfig.h` 不生成 → 编译报 `fatal error: 'tif_config.h' file not found`。
  配方在 `PATH` 头部注入 uname shim（`-s`→`Linux`、`-r`→`6.6`、`-m`→`aarch64`），并把
  `compat/**/config.guess` 桩化为固定输出 `aarch64-unknown-linux-gnu`
  （因为 `conanbuild.sh` 会前置 profile 的 PATH，可能盖住 shim）。
- **TEA 探测缓存变量**：`tcl_cv_sys_version=Linux-6.6`、`ac_cv_prog_cc_works=yes`
  供 `SHLIB_LD` 探测使用，否则生成的共享库链接命令不正确。
- **E011**：HMDFS 拒绝 0600 临时目录，源码树内 28 个 `configure` 的 `umask 077` 改写为 `022`。
- **只用 `AutotoolsToolchain`，不用 `AutotoolsDeps`**：后者会把依赖的
  `LIBS="-ltcl9tk9.0 -ltcl9.0 …"` 注入每个 conftest 的链接命令 → 宿主上
  `configure: error: cannot run C compiled programs`。
- **`tkConfig.sh` 路径修复**：tk 包发行的 `tkConfig.sh` 含
  `TK_LIB_SPEC='-L//lib -ltcl9tk9.0'`、`TK_STUB_LIB_SPEC='-L//lib -ltkstub'`、
  `TK_INCLUDE_SPEC='-I//include'`，tcl 包 `tclConfig.sh` 含 `TCL_PREFIX='${TCL_ROOT}'`
  → `ld.lld: error: unable to find library -ltclstub / -ltkstub`。
  配方改写生成的 Makefile，把这些路径指向 tcl / tk 包内的真实 `lib/`。
- **X11**：`TEA_PATH_X` 在 OHOS 找不到 X11，退化为裸 `-lX11`，需补
  `-L<libx11包>/lib`；且 `window/window.c` 直接 `#include "X11/Xproto.h"`，该头既不在
  libx11 包也不在 tk 包 → 依赖 header-library `xorgproto` 并把其 `include` 加入 `CPPFLAGS`。
- **运行期**：处理器经 `tkConfig.sh` 的 `SHLIB_LD_LIBS` 链接了 `libX11.so.6`，
  故消费者运行期还需 `libxcb.so.1`（连带 `libxau`、`libxdmcp`）在 `LD_LIBRARY_PATH` 上。
- **上游测试解释器**：`tclsh` 不在宿主默认 `PATH`（来自 tcl 包），上游 Makefile 的
  `tcltests` 目标（裸 `tclsh`）在 CI 会 127；配方改用 tcl 包内 `bin/tclsh9.0` 绝对路径
  执行同一入口 `tests/all.tcl`，并用无缓冲包装器 + `timeout` 包裹（OHOS 上解释器退出
  路径可能被 Tk 拆除拖住）。

## 排除与替代

- 上游 `tests/visualtests`（需真实显示设备、人工目视）与 `tests/dpitests`（需屏幕 DPI）
  不纳入自动化验证；`make test` 目标包含它们，故不使用 `make test`，只执行 `tcltests` 入口。
- PDF 读写依赖外部 **Ghostscript**（`gs`），OHOS 宿主默认不提供；因此
  `pdf.test` / `ps.test` 中 18 个用例在上游同款约束下跳过（与平台适配无关）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| tk | 9.0.3.2 | `--with-tk` 需要 `tkConfig.sh`；自动带来 tcl |
| tcl | 9.0.3.2 | tk 的传递依赖；提供消费者与上游测试解释器 `tclsh9.0` |
| libx11 | 1.8.13 | `window` / `xpm` 处理器链接 `-lX11` |
| libxcb | 1.17.0 | libx11 的传递依赖（运行期必需） |
| libxau | 1.0.11 | libxcb 的传递依赖 |
| libxdmcp | 1.1.5 | libxcb 的传递依赖 |
| xorgproto | 2025.1 | 提供 `X11/Xproto.h`（header-library） |
| xtrans | 1.4.0 | libx11 的传递依赖（仅配方/头） |
| xcb-proto | 1.17.0 | libxcb 的传递依赖（仅配方生成用） |

`compat/` 自带的 zlib / libpng / libtiff / libjpeg **不**需要外部 conan 包。

## 功能验证

```bash
# 消费者视角：用 tcl 包的 tclsh9.0 加载本包并做一次真实图像往返
TCLLIBPATH="<pkg>/lib/Img2.1.1 <tcl包>/lib <tk包>/lib" \
LD_LIBRARY_PATH="<tcl包>/lib:<tk包>/lib:<libx11包>/lib:<libxcb包>/lib" \
<tcl包>/bin/tclsh9.0 -c 'package require Img'   # → 2.1.1
```

`conan create archives/l/libtk-img/2.1.1 -pr:h/-pr:b=<ohos-aarch64> --build=missing`
会自动执行三层验证：`build()` 内的上游 `tests/all.tcl`（含新增 `tests/ohos.test` 25 例）、
`test_package`（31 项断言），产物位于 `<pkg>/lib/Img2.1.1/`（24 个 `.so` + `pkgIndex.tcl`）。

## 参考

- 官网: https://sourceforge.net/projects/tkimg/
- 源码发行: https://downloads.sourceforge.net/project/tkimg/tkimg/2.1/tkimg%202.1.1/Img-2.1.1.tar.gz
