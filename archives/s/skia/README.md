# Skia（HarmonyOS PC 适配）

Skia 是 Google 的**开源 2D 图形引擎**：为 Chrome / Android / Flutter / ChromeOS 等提供跨平台的
几何、文本与图像渲染能力。核心是**软件光栅化器**（CPU 渲染），另有 **Ganesh** GPU 后端、
PDF/SVG 编码、图像编解码（PNG/JPEG/WebP/GIF/RAW）与文本整形（HarfBuzz + ICU）。

## 功能概述

- **CPU 光栅化核心**：`SkCanvas` / `SkSurface::MakeRaster*` / `SkPaint` / `SkPath` / `SkImage`（本适配的**核心交付面，零裁剪**）
- **图像编解码**：libpng / libjpeg-turbo / libwebp / libgifcodec / dng_sdk(+piex)（`SkCodec` / `SkPngEncoder` 等）
- **文本**：freetype2 + harfbuzz（+ ICU 做 bidi/分段），`SkShaper`
- **PDF / SVG**：`SkPDF`（含 harfbuzz 字体子集）、`modules/svg`
- **GPU 后端**：Ganesh GL(GLES/EGL) —— 代码面保留，接口按 OHOS 可达性走 EGL

## 版本口径（重要）

skia **本体没有语义版本号**。本仓版本 `2.88.9` = **SkiaSharp binding 版本**
（`github.com/mono/SkiaSharp` tag `v2.88.9`）；其 `externals/skia` submodule（skia-native 快照，
指向 fork `github.com/mono/skia`，分支 `xamarin-mobile-bindings`）pin 到
commit `4bed689c9c9eb77a120c6a9d54af6a572c85d1c2`（2024-10-11）。源码 tarball 与 sha256 见 `2.88.9/conandata.yml`。

## OHOS 适配要点

1. **GN 工具链自举**：skia 的 `bin/fetch-gn` 从 `chrome-infra-packages` 抓 x86 预编译 gn
   （OHOS 不可达且不可执行），故用 **OHOS clang 从 gn 源码自举**；产物还要放到源码树 `bin/gn`
   （`gen/skia.h` action 会调用 `gn desc`）。
2. **GPU/GL 接口**：OHOS 无 X11 → `skia_use_egl=true`（sysroot 提供 EGL/GLES 头 + `libEGL.so`），
   这也是 OHOS 上唯一可构建的 GL 原生接口（`glx` 分支需要 X11 头）。
3. **第三方依赖**：上游用 `DEPS` + `gclient` 从 `*.googlesource.com` 抓第三方源码（OHOS 不可达）
   → 全部改 **GitHub 镜像**并逐条核对**同一 commit SHA**（AOSP 系用 `msft-mirror-aosp`），逐条 sha256 pin。
4. **ICU**：OHOS sysroot 只带 ICU 公共 C API 头（`UText` 内部结构体与 C++ 头被裁掉），
   而 `SkShaper` 需要完整 `UText` → 配方补齐与 sysroot `libicu.so`（ICU 72.1）同版本的完整头。
5. **musl 差异**：无 `__WORDSIZE`（glibc 专有）→ `extra_cflags=["-D__WORDSIZE=64"]`；
   harfbuzz 新版删除了 skia 仍在用的 `hb_subset` 旧 API → 见 `2.88.9/patches/`。

## 依赖关系

- 编译依赖：OHOS clang 15（系统）、ninja（conan `tool_requires`）、python3；GN 源码（自举）；
  ICU 72.1 头；13 个 third_party 源码包（GitHub 镜像，sha256 pin）
- 运行依赖：OHOS 系统库 `libicu.so` / `libEGL.so` / libc(pthread,dl,m)

## 参考资料

- 官网：https://skia.org ｜ 源码：https://github.com/mono/skia（SkiaSharp 绑定版）
- 适配笔记：`2.88.9/notes.md`
