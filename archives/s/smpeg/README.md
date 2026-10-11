# smpeg

SDL MPEG 播放库（LGPL）：MPEG-1 音视频解码核心 `libsmpeg` + 官方示例播放器 `plaympeg`。

- 上游项目：https://www.libsdl.org/projects/smpeg/
- 源码：`https://deb.debian.org/debian/pool/main/s/smpeg/smpeg_0.4.5+cvs20030824.orig.tar.gz`
  （sha256 `1276ea797dd9fde8a12dd3f33f180153922544c28ca9fc7b477c018876be1916`，Debian 官方归档）
- 版本：`0.4.5-cvs20030824`（2003 年 CVS 快照，与赛事清单一致）

## 功能概述

- MPEG-1 系统流/音频/视频解码，输出 SDL 音频回调与视频帧
- 提供 C API（`SMPEG_new` / `SMPEG_play` / `SMPEG_getinfo` …）与示例播放器 `plaympeg`
- 被 SDL_mixer 等库作为 MP3 解码后端使用

## OHOS 适配

构建系统为 2003 年的 autotools（tarball 自带生成好的 `configure`），依赖制品仓 `sdl/1.2.15`。
四个可移植性补丁（见 `patches/`）：

1. **C++17 源码现代化**：`register` 存储类在 C++17 被移除（13 个文件、87 处）；表格初始化里的
   `0-1` 哨兵在 C++11 起属于列表初始化窄化错误；`MPEGaudio.h` 的 `friend` 声明现代编译器不再
   引入到外层命名空间 → 补齐了命名空间级声明。
2. **libtool 链接驱动**：上游 `libsmpeg_la_LDFLAGS` 硬编码 `-lstdc++`（并把 `CXXLD` 固定为 `cc`），
   OHOS 只有 libc++ → 改为 `-lc++`。
3. **config.sub 补 aarch64/ohos**（与 `aalib/1.4p5` 同一三行补丁）。
4. **config.status 临时目录 umask 077 → 022**（HMDFS 会把新目录标成 setgid，077 目录不可用，E129/E011）。

另外：制品仓 `sdl/1.2.15` 不提供 `sdl-config` 脚本，而上游 `AM_PATH_SDL` 必须执行它 →
配方在构建目录生成等价的 `sdl-config` 外壳（同样处理见 `sdl_mixer/1.2.12`、`lbreakout2/2.6.5`）。

## 依赖关系

- 编译/运行依赖：`sdl/1.2.15`（静态库 SDL，运行期会用到其 alsa 后端）
- 无其他第三方依赖
