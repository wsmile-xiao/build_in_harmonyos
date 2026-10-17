# mencoder

MEncoder 是 MPlayer 项目自带的命令行音视频编码/转码工具，可把任意 MPlayer 能解码的输入转换为多种输出格式（AVI/MPEG-4/MPEG/Matroska 等）。

## 功能概述

- 命令行视频编码与转码（`-ovc`/`-oac` 选择视频、音频编码器，默认走内置 `lavc`（FFmpeg libavcodec））
- 多格式输出封装：AVI、MPEG-4、MPEG-PS/TS、Matroska、rawvideo 等
- 按时间区间裁剪、缩放、帧率转换、滤镜链（`-vf`）
- 两遍编码、码率/质量参数控制（`-lavcopts`）
- 音频编码：MP3（lame）、AC3、PCM、AAC 等

## OHOS 适配

- **构建裁剪**：鸿蒙侧只交付 MEncoder 命令行工具，配置为 `--disable-mplayer --disable-gui --disable-x11 --disable-networking`，不构建 MPlayer 播放器主体、GUI 与视频输出子系统（`libvo`）。
- **FFmpeg 依赖**：使用官方 `ffmpeg-6.1.6` 源码单独配置（`--disable-autodetect --disable-everything` + 按需 `--enable-*`），避免内嵌 FFmpeg 主线与 r38542 的旧 API 不兼容；同时禁用 FFmpeg 网络组件，规避 MEncoder 禁用网络后仍残留网络对象符号的问题。
- **平台差异**：产物为 OHOS aarch64 动态可执行文件（`PT_INTERP = ld-musl-aarch64.so.1`，含链接器写入的 `.note.ohos.ident` 段，不依赖 glibc）。
- **已知问题**：二进制版本字符串显示为 `UNKNOWN-15.0.4`——上游通过 `svn info` 探测 SVN 修订号生成版本串，源码树无 SVN 元数据时回退为该值，不影响功能。
- 无平台补丁（`patches/` 为空）。

## 依赖关系

| 类型 | 依赖 | 说明 |
|------|------|------|
| 编译依赖 | ffmpeg 6.1.6（源码内置） | 提供 libavcodec / libavformat / libavutil / libswscale 等 |
| 运行依赖 | OHOS musl 运行时（系统提供） | 无额外动态库依赖 |

## 安装

```bash
curl install.sh | sh -s -- mencoder 38542
```

## 验证

```bash
mencoder -ovc help          # 列出可用视频编码器，应包含 lavc
```

## 使用示例

```bash
# 原始 I420 帧编码为 MPEG-4 AVI
mencoder -demuxer rawvideo -rawvideo w=16:h=16:fps=25:format=i420 \
         input.yuv -ovc lavc -lavcopts vcodec=mpeg4 -o output.avi

# 按时间区间转码并缩放
mencoder input.avi -ss 00:00:10 -endpos 00:00:30 -ovc lavc -oac lavc \
         -vf scale=640:480 -o clip.avi
```

## 参考资料

- 官网：https://www.mplayerhq.hu/
- 源码仓库：https://svn.mplayerhq.hu/mplayer/trunk （SVN，本包固定 revision 38542）
- 文档：`man mencoder`（安装后位于 `share/man/man1/mencoder.1`）
