# libxosd 2.2.14 — OpenHarmony PC (OHOS aarch64) 适配笔记

## 上游
- 项目：xosd（X On-Screen Display），库名 libxosd，主页 https://sourceforge.net/projects/libxosd/。
- 版本 2.2.14（事实最新稳定版，全发行版同版）。语言 **C**。
- 源码：Debian pool 的 `xosd_2.2.14.orig.tar.gz` == 上游 `xosd-2.2.14.tar.gz`（无 repack，sha256 已核对一致：418331 字节）。SourceForge 主镜像从 OHOS CI 不可达，故 conandata 用 Debian pool 直链。

## 真实依赖闭包（实测，修正早期"含 freetype/Xrandr"误判）
- **libx11/6.4.0**（X11 客户端库 + `Xlib.h` 等头文件；经它间接拉 libxcb/1.16、xtrans/1.6.0、xorgproto）
- **libxext/6.4.0**（XShape 扩展；`libxosd.c` 调用 `XShapeCombineMask` / `XShapeQueryExtension`）
- **libxinerama/1.1.5**（Xinerama 扩展；`libxosd.c` 调用 `XineramaQueryExtension` / `XineramaQueryScreens` / `XineramaIsActive`）
- **xorgproto/2025.1**（X11 协议头 `Xfuncproto` / `Xmd` 等）
- **pthread**（系统）
- **不含 freetype / Xrandr**：`grep src/` 零匹配。`xosd 2.2.14` 用 X11 核心字体（`XLoadQueryFont`），不链接 freetype2；`Xrandr` 亦未使用。早期可行性分析误把 freetype/Xrandr 列为依赖，已订正。

### 为什么用 6.4.0 统一线（而非旧线 1.8.x / 1.3.x）
- 仓库里的 X.Org 库有两条并行线：**旧线** `libx11/1.8.13`、`libxext/1.3.7`（带 R37 债务：`libx11/1.8.13` 精确钉 `libxcb/1.17.0`，而仓里只有改名后的 `libxcb/1.17.0.1`，解析即失败）；**新线** `libx11/6.4.0`、`libxext/6.4.0`（统一 6.x 版本，钉 `libxcb/1.16`，干净）。
- `libxinerama/1.1.5` 已经在用 6.4.0 线。若 xosd 走旧线（`libx11/1.8.13.1` + `libxext/1.3.7`），会与 libxinerama 拉入的 6.4.0 形成**两套 libX11/libXext 共存**（SONAME 同为 `.so.6`/`.so.2`），运行时动态链接不确定、有 ABI 崩溃风险，且旧线依赖尚未发布的 `libx11/1.8.13.1`（仅存于未合并的修复 PR #15161）。
- 因此 xosd 整体切到 6.4.0 栈：单一 X11 版本、无 R37 债务、与 libxinerama 完全一致、远端 CI 可直接解析（6.4.0 栈已在 ohpcd 发布二进制）。全链 `libxau/1.0.11 → xtrans/1.6.0 → libxcb/1.16 → libx11/6.4.0 → libxext/6.4.0 → libxinerama/1.1.5 → xosd` 均从 ohpcd 拉到预构建二进制，仅 xosd 自身本地从源码构建。

## 关键适配点
1. **2004 老 autotools**：自带 `config.sub` / `config.guess`（2004）不认 `aarch64` → 用 GNU savannah 现代版替换（随配方附带 `config.sub` / `config.guess`）。
2. **旧 libtool 1.5**：`ltmain.sh` 2004，靠 config.sub 接受 aarch64 后，其 `linux*` 分支可正常产出 `.so`。
3. **configure 补丁（OHOS）**：`umask 077`→`022`（E002/HMDFS 临时目录）；shebang `#!/bin/sh`→`/data/service/hnp/bin/bash`（configure 用 `==` 测试，dash 不支持）。
4. **X11 探测**：`AC_PATH_XTRA` 经 `--x-includes` / `--x-libraries` 指向 libx11 安装目录，避免定义 `X_DISPLAY_MISSING` 导致 `libxosd.c` 编译失败。
5. **Xext/Xinerama 链接**：上游 Makefile 仅以 `$(X_LIBS)`（= libX11）链接 `libxosd.la`，但 `libxosd.c` 实际调用 XShape / Xinerama 符号 → configure 后 patch `src/libxosd/Makefile` 的 `libxosd_la_LIBADD` 追加 `-lXext -lXinerama`，使 `libxosd.so` 正确 NEEDED `libXext` / `libXinerama`。
6. **依赖传递**：`cpp_info.requires = ["libx11::libx11", "libxext::libxext", "libxinerama::libxinerama", "xorgproto::xorgproto"]`（Conan 2 要求按 `包名::组件` 格式，且**必须把每一个直接依赖都列上**，否则 `package_info()` 报 "direct dependency not used by any requires"）。消费者（含 osdclock）经 CMakeDeps 自动传递链接 X11 / Xext / Xinerama。
7. **插件禁用**：`--disable-new-plugin` 关闭 xmms 新插件（需 GTK 1.2 / XMMS / gdk-pixbuf，未移植）；bmp 插件受限于 `bmp` 包不存在而保持关闭；old-plugin 默认关闭。
8. **configure 探测不可带 X11 链接库（实测踩坑）**：`generate()` 注入环境变量时，若把 `-lX11 -lXext -lXinerama` 放进 `LIBS`，configure 的"编译器是否可用"测试程序也会被强制链接这些 `.so`，而它们不在构建期运行时 loader 路径里 → `Error loading shared library libX11.so.6` → "cannot run C compiled programs"。正确做法：`LIBS` 只留 `-lpthread`（供 configure 的 pthread 探测），X11/Xext/Xinerama 的实际链接完全交给 Makefile 的 `libxosd_la_LIBADD` 补丁（`-lX11 -lXext -lXinerama`）；`CPPFLAGS`(-I)/`LDFLAGS`(-L) 仍可注入用于找头文件与库。

## 测试
- 上游无独立 test suite（`make check` 仅覆盖 xmms/bmp 插件，不适用）。
- test_package：display-free 消费者冒烟测试——链接 libxosd、读取 `osd_default_font` / `osd_default_colour` 全局符号、取 `xosd_set_bar_length` 函数地址，验证库可链接 / 加载且 API 符号完整（无需 X server）。
