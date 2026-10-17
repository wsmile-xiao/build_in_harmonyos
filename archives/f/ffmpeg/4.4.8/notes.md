# ffmpeg 4.4.8 编译笔记（HarmonyOS PC · 原生 conan create）

## 定位

release/4.4，Ubuntu 22.04 LTS / 老 Android 与嵌入式 SDK 所用。与本仓其它 ffmpeg 版本**并存**：各代 soname 完全不同，可同时装在设备上互不冲突，
由消费方按 ABI 需求选择。

本版 soname：avutil 56 / avcodec 58 / avformat 58 / avdevice 58 / avfilter 7 / swscale 5 / swresample 3

## 关键适配

本配方由已在真机验证通过的 `7.1.5` 配方派生。FFmpeg 在鸿蒙 PC 上的固有适配点见
`archives/f/ffmpeg/7.1.5/notes.md`（configure 非 autoconf、`--target-os=linux`、install 破坏签名、
`--disable-autodetect` 连带关 pthreads、`.pc` 路径重定位、prefix 时机等），此处只记本版差异。

### 本版 drawtext **不需要** harfbuzz（与 6.1+ 的关键差异）

`drawtext_filter_deps="libfreetype"` —— 只要 freetype。而且本版 configure **根本没有 `libharfbuzz`
这个选项**，照抄 6.1+ 的配方传 `--enable-libharfbuzz` 会被 `die_unknown` 当场打死。
故本配方相比 6.1+ 少一个依赖、少一个 configure 开关、`avfilter` component 也不引用 `harfbuzz::harfbuzz`。

## 外部编解码器与功能库

11 个依赖全部来自制品仓，均为 BSD/LGPL，**不引入 GPL 传染**
（未启用 `--enable-gpl`/`--enable-nonfree`；选 openh264 而非 x264/x265，后者会强制 `--enable-gpl`）：

`zlib` `bzip2` `xz` `openssl`(https/tls) `freetype` `fontconfig`(drawtext)
`libxml2`(dash) `openh264`(H.264 编码) `libvpx`(VP8/VP9) `opus` `lame`(MP3)

## 真机验证结果（2026-07-27，设备 3QC0124C11000718）

`conan create . -pr ohos-native -r <remote> --build=missing` **rc=0，276s**，包体积 28M，
package_id `03fb2cd5…`。

- 实际库版本：libavcodec 58.134.100 / libavformat 58.76.100 / libavfilter 7.110.100
- 七个 `.so` 的 SONAME 与预期一致，9 个 ELF（7 库 + `bin/ffmpeg` + `bin/ffprobe`）均含 `.codesign` 段
- **test_package 8 条断言全绿**：内建 mpeg4 真编一帧；libopenh264 / libvpx / libopus / libmp3lame
  四个外部编码器均已注册；libopenh264 真编一帧（454 字节）；`https` 协议存在（openssl 接线证据）；
  `drawtext` 滤镜存在（freetype + fontconfig 接线证据）
- 打包时三道硬检查全过，含**检查 C**（用制品仓依赖解析重算 package_id 比对一致）

## 已知限制

- **subtitles / ass 滤镜**：需 `libass`，制品仓暂无
- **无硬件加速**：鸿蒙 PC 无 VAAPI/VDPAU/NVDEC，FFmpeg 亦无 OHOS hwaccel 后端，为纯软编软解
- **无 iconv**：属 autodetect，未启用
- **无 ffplay**：需 SDL2，设备无

## 状态

built —— 真机 `conan create` + test_package(8 断言) + 外部编解码器接线全绿，制品已上传制品仓。
