# FFmpeg 6.1.5 编译笔记

## 编译过程

### 1. 初始化
- 软件名: ffmpeg
- 版本: 6.1.5（最新 release 版）
- 源码下载: ffmpeg-6.1.5.tar.xz
- 构建系统: 自定义 configure 脚本（非标准 autotools）

### 2. 预扫描发现问题

预编译风险扫描发现两个关键问题：

#### PSCAN-FS-001: /tmp 硬编码
- **文件**: `libavutil/file_open.c:140`
- **问题**: 硬编码 `/tmp` 路径，OpenHarmony 上 `/tmp` 为只读 erofs
- **修复**: 使用 `#ifdef __OHOS__` 守卫，替换为 `/data/local/tmp`

#### PSCAN-MUSL-001: pthread_cancel 不可用
- **文件**: `libavformat/udp.c:1133`
- **问题**: musl libc 不支持 `pthread_cancel`
- **修复**: 使用 `#ifdef __OHOS__` 守卫，用 `shutdown(SHUT_RD)` 替代

### 3. Configure

configure 脚本执行成功，配置了以下主要组件：
- 编解码器: H.264, H.265, VP8, VP9, AAC, MP3 等
- 输入设备: fbdev, lavfi, oss, v4l2
- 输出设备: fbdev, oss, v4l2
- 协议: file, http, tcp, udp 等

**注意事项**:
- TMPDIR 需设置为 `$HOME/tmp`（默认 tmpexport 不支持 FIFO）
- 使用单线程编译 (`make -j1`) 避免 jobserver 问题

### 4. 编译

- 编译时间: 约 32 分钟（单线程）
- 编译警告: 部分类型转换警告（不影响功能）
- 编译产物: ffmpeg, ffprobe（已 stripped）

### 5. 安装

- 安装目录: `$HOME/usr/local`
- staging 目录: `$HOME/tmp/test-install-ffmpeg-6.1.5`

### 6. 打包

生成两个预编译包：
- `ffmpeg-6.1.5-ohos-aarch64.tar.gz` (216M) - stripped 版本
- `ffmpeg-6.1.5-ohos-aarch64-debug.tar.gz` (331M) - 包含调试符号

---

**编译结束**: 2026-05-22
**最终状态**: built

**编译者**: OpenDesk Agent