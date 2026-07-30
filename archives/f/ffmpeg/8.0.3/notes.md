# ffmpeg 8.0.3 编译笔记（HarmonyOS PC · 原生 conan create）

## 定位

release/8.0（8.1 的前一条功能线）。与本仓其它 ffmpeg 版本**并存**：各代 soname 完全不同，可同时装在设备上互不冲突，
由消费方按 ABI 需求选择。

本版 soname：avutil 60 / avcodec 62 / avformat 62 / avdevice 62 / avfilter 11 / swscale 9 / swresample 6

## 关键适配

本配方由已在真机验证通过的 `7.1.5` 配方派生。FFmpeg 在鸿蒙 PC 上的固有适配点见
`archives/f/ffmpeg/7.1.5/notes.md`（configure 非 autoconf、`--target-os=linux`、install 破坏签名、
`--disable-autodetect` 连带关 pthreads、`.pc` 路径重定位、prefix 时机等），此处只记本版差异。

### 本版 drawtext 需要 harfbuzz

`drawtext_filter_deps="libfreetype libharfbuzz"` —— 除 freetype（字形光栅化）外还硬依赖 harfbuzz
（文本整形），**缺任一个 configure 不报错、只是静默不生成该滤镜**。

## 外部编解码器与功能库

12 个依赖全部来自制品仓，均为 BSD/LGPL，**不引入 GPL 传染**
（未启用 `--enable-gpl`/`--enable-nonfree`；选 openh264 而非 x264/x265，后者会强制 `--enable-gpl`）：

`zlib` `bzip2` `xz` `openssl`(https/tls) `freetype` `harfbuzz/14.2.0` + `fontconfig`(drawtext)
`libxml2`(dash) `openh264`(H.264 编码) `libvpx`(VP8/VP9) `opus` `lame`(MP3)

## 真机验证结果（2026-07-27，设备 3QC0124C11000718）

`conan create . -pr ohos-native -r <remote> --build=missing` **rc=0，291s**，包体积 31M，
package_id `55a18723…`。

- 实际库版本：libavcodec 62.11.103 / libavformat 62.3.103 / libavfilter 11.4.103
- 七个 `.so` 的 SONAME 与预期一致，9 个 ELF（7 库 + `bin/ffmpeg` + `bin/ffprobe`）均含 `.codesign` 段
- **test_package 8 条断言全绿**：内建 mpeg4 真编一帧；libopenh264 / libvpx / libopus / libmp3lame
  四个外部编码器均已注册；libopenh264 真编一帧（360 字节）；`https` 协议存在（openssl 接线证据）；
  `drawtext` 滤镜存在（freetype + harfbuzz + fontconfig 接线证据）
- 打包时三道硬检查全过，含**检查 C**（用制品仓依赖解析重算 package_id 比对一致）

## 已知限制

- **subtitles / ass 滤镜**：需 `libass`，制品仓暂无
- **无硬件加速**：鸿蒙 PC 无 VAAPI/VDPAU/NVDEC，FFmpeg 亦无 OHOS hwaccel 后端，为纯软编软解
- **无 iconv**：属 autodetect，未启用
- **无 ffplay**：需 SDL2，设备无

## 状态

built —— 真机 `conan create` + test_package(8 断言) + 外部编解码器接线全绿，制品已上传制品仓。

> **补注（harfbuzz 的版本界限）**：该依赖是 **6.1 引入**的，不是 7.0——实测 `ffmpeg-6.0.1/configure`
> 里 `drawtext_filter_deps="libfreetype"` 且无 `libharfbuzz` 选项，`6.1.6` 起才变为
> `"libfreetype libharfbuzz"`。本目录 `conanfile.py` 的注释写「7.0 起」，对 8.0.x 而言结论不受影响
> （8.0 > 7.0），未为一句注释改动 recipe（改它会变 rrev、须重发制品）。以本文件为准。
