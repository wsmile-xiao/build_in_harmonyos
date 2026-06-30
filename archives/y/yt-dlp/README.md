# yt-dlp

yt-dlp 是一个功能丰富的命令行音频/视频下载器，基于 youtube-dl 的增强版本。

## 特性

- 支持数千个视频网站（YouTube、Vimeo 等）
- 下载视频、音频、字幕
- 支持多种输出格式和质量选择
- SponsorBlock 集成
- 视频切片和合并
- 元数据嵌入
- 播放列表和频道下载

## 构建系统

Python zipapp (打包单文件可执行程序)

## 依赖

- Python 3.10+ (运行时)

## OpenHarmony 适配

yt-dlp 以自包含的 Python zipapp 格式分发：
- 无需编译
- 无外部依赖（仅需 Python 3）
- 解压后可直接执行

### 安装

```bash
# 解压预编译包
tar xzf yt-dlp-2026.03.17-ohos-aarch64.tar.gz -C $HOME/usr/local

# 验证安装
yt-dlp --version
```

### 已知限制

无。yt-dlp 在 OpenHarmony 上无需任何平台特定修改即可运行。

## 版本信息

- 当前版本：2026.03.17
- 发布日期：2026-03-17
- 来源：https://github.com/yt-dlp/yt-dlp

## 使用示例

```bash
# 下载视频
yt-dlp "https://www.youtube.com/watch?v=VIDEO_ID"

# 下载最佳质量
yt-dlp -f "bestvideo+bestaudio" "URL"

# 仅提取音频
yt-dlp -x --audio-format mp3 "URL"

# 下载播放列表
yt-dlp "https://www.youtube.com/playlist?list=PLAYLIST_ID"

# 更新 yt-dlp
yt-dlp -U
```