# HandBrake

HandBrake 是一款开源的跨平台视频转码工具，本项目适配其命令行版本 **HandBrakeCLI 1.11.2**（OpenHarmony PC / aarch64）。

## 功能概述

- 视频转码：H.264 (x264)、H.265 (x265)、VP8/VP9 (libvpx)、AV1 (SVT-AV1)、Theora 等
- 音频转码：AAC、MP3 (lame)、Opus、Vorbis、AC3/E-AC3、FLAC 等（内置 ffmpeg 编解码）
- 封装格式：MP4/MKV/WebM（Matroska/MP4/WebM muxer）
- 字幕支持：SRT/ASS/SSA/PGS 等（libass 渲染）
- 滤镜：裁剪、缩放（zimg）、去隔行（yadif/bwdif）、降噪（nlmeans）等
- 命令行批处理转码能力（`HandBrakeCLI`）

## OHOS 适配

- **构建系统**：HandBrake 顶层使用自定义 configure（`make/configure.py`，Python 驱动），生成 `build/` 下的 GNUmakefile；全部 33 个 contrib 在树内构建，不依赖 Conan 外部包。
- **平台识别**：`make/config.guess` 补 HarmonyOS build tuple（`aarch64-unknown-linux-ohos`）；contrib 内（freetype/lame/libass/libiconv/libspeex/libvorbis/x264/xz 等）逐个补 A01-config-guess 补丁（E007）。
- **功能裁剪**：禁用 GTK GUI、NUMA、所有硬件编码器（NVENC/NVDEC/QSV/VCE/MF）、libdovi，仅产出 `HandBrakeCLI`。
- **ELF 签名**：OHOS 上未签名二进制报 `Operation not permitted`，`package()` 内用 `binary-sign-tool` 自签名（selfSign）。
- **与 Linux 差异**：HMDFS 上 make jobserver mkfifo 不可用（警告无害）；后台进程会被杀，构建必须前台执行。

## 依赖关系

- 编译依赖（contrib，全部在树内）：ffmpeg 8.0.2、x264、x265、libvpx 1.16、libass、libdav1d 1.5.3、SVT-AV1 4.1.0、zlib 1.3.2、bzip2、libiconv、freetype、harfbuzz、fribidi、lame 3.100、libopus、libvorbis、libtheora、libspeex、jansson、libjpeg-turbo、libbluray、libdvdread/dvdnav、libgnurx、xz、zimg 等
- 运行依赖：仅系统基础运行时（libc/libm/libdl/pthread）

## 参考资料

- 官网：https://handbrake.fr
- 源码仓库：https://github.com/HandBrake/HandBrake
- 版本归档：`archives/h/handbrake/1.11.2/`
