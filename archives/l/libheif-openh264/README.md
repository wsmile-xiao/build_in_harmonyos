# libheif-openh264

`libheif` 1.23.0 的 **OpenH264（H.264/AVC）解码后端插件** 子包。

## 描述

libheif 从 1.19 起把编解码后端做成可独立装载的插件：宿主 `libheif.so` 在
`heif_init()` 时扫描插件目录（默认 `<libdir>/libheif`），把其中的 `*.so` 逐个 `dlopen`，
读 `plugin_info` 注册后端。本包交付的就是这套体系里 **OpenH264 解码器**那一份：

- 上游 CMake 目标 `heif-openh264dec` → 产物 `lib/libheif/libheif-openh264dec.so`（MODULE 插件）；
- 以及它**无法脱离**的宿主 `lib/libheif.so`（同源同版本、`ENABLE_PLUGIN_LOADING=ON`）、
  `include/libheif/*.h`、`lib/pkgconfig/libheif.pc`、`lib/cmake/libheif/*`。

能力边界：只提供 **AVC 解码**。上游把 OpenH264 编码器目标注释掉了
（`CMakeLists.txt:201` 的 `# plugin_option(OpenH264_ENCODER ...)`），因此
`heif_have_encoder_for_format(heif_compression_AVC)` 恒为 0。

## 版本

| 版本 | 状态 | 备注 |
|------|------|------|
| 1.23.0 | built | 源码 = 父 tarball `libheif` 1.23.0；依赖 `openh264/2.6.0`；无补丁 |

## 依赖

- `openh264/2.6.0`（shared，SONAME `libopenh264.so.7`）—— 唯一直接依赖
- 其余 libheif 后端（libde265/x265/aom/dav1d/x264/kvazaar/uvg266/vvdec/vvenc/openjpeg/
  openjph/ffmpeg/rav1e/svt/jpeg/libsharpyuv）在本包配方里全部显式 OFF

## 同族子包

`libheif-libde265` / `libheif-openjpeg` / `libheif-svtenc` / `libheif-aom` /
`libheif-dav1d` / `libheif-jpeg` —— 每个都是「自包含宿主 + 单个后端插件」形态。
**同一进程内不要混装多个子包**：各自携带一份同版本宿主，会造成插件注册表分裂。

## 相关链接

- 上游: https://github.com/strukturag/libheif
- OpenH264: https://github.com/cisco/openh264
