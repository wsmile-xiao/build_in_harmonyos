# musikcube 3.0.5 HarmonyOS PC 适配记录

## 适配范围

上游：`https://github.com/clangen/musikcube`，tag `3.0.5`。
源码 SHA256：`708292a583bb5072a8dbb14e408c2a1f61de9b8c9786d4e53b3e69bef5dad8c5`。

## 依赖与裁剪

Conan 直接消费已发布的 sqlite3/3.49.1、zlib/1.3.1、libcurl/8.5.0、taglib/2.3、ncurses/6.5 和 ffmpeg/7.1.5。libmicrohttpd 未发布，因此裁剪 server/remote 插件；systemd/DBus 相关 mpris 插件同步裁剪。

## 音频后端裁剪链

1. 禁用 ALSA、PulseAudio、PipeWire、CoreAudio、sndio、PortAudio 输出插件；
2. 不添加空壳音频后端，仅保留上游 `nullout`；
3. 裁剪 server/remote 插件及 libmicrohttpd 依赖；
4. 裁剪 FFmpeg 解码及其他未纳入最小核心交付的插件；
5. 交付 musikcore 核心库、索引与元数据能力。

本适配不验证实际音频播放，不能作为 HarmonyOS PC 本地播放器使用。目标 ELF 的 test_package 运行验证交由 CI；本地 noexec 环境不执行目标 ELF。
