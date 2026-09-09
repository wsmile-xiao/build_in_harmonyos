# musikcube 3.0.5 HarmonyOS PC 适配记录

上游：`https://github.com/clangen/musikcube`，tag `3.0.5`。
源码 SHA256：`708292a583bb5072a8dbb14e408c2a1f61de9b8c9786d4e53b3e69bef5dad8c5`。

## 适配范围

交付 musikcore 核心库、索引与元数据能力，并保留 taglibreader、nullout、httpdatastream、supereqdsp 插件。libmicrohttpd 未发布，故裁剪 server；systemd/DBus 不可用于 OHOS，故裁剪 mpris；所有本地音频输出插件均裁剪，FFmpeg 解码及其他非核心插件裁剪。

## 依赖与裁剪

直接消费 sqlite3/3.49.1、zlib/1.3.1.1、libcurl/8.5.0、taglib/2.3、ncurses/6.5、libev/4.33、openssl/3.5.6。libmicrohttpd 未发布，不混入本 PR。

## Asio 处理（方案 A′）

musikcore 的 RemoteLibrary/PiggyDebugBackend 仍由上游直接编译 websocketpp/standalone Asio 代码，无法仅裁掉 musikcubed。官方 musikcube 归档不包含其 git submodule 内容，因此 conandata.yml 增加官方 Asio 1.30.2 tarball 条目，保持独立 vendored 头文件，不创建独立 Conan 包；source() 将其安装到 `src/3rdparty/asio/`，使 `asio/version.hpp` 可见。Asio SHA256 为 `755bd7f85a4b269c67ae0ea254907c078d408cce8e1a352ad2ed664d233780e8`。

## 本地验证记录

test_package CTest（本地，clang-15-armv8-17-release，Sep 06 14:55 CST）：`musikcube_core_test` 1/1 Test Passed（CTestCostData.txt：`musikcube_core_test 1 0.155703`，LastTest.log：`Test Passed.`）。

## 音频后端限制

禁用 ALSA、PulseAudio、PipeWire、CoreAudio、sndio、PortAudio；不添加空壳后端，仅保留上游 nullout。server/remote 插件与 FFmpeg 解码插件按裁剪阶梯移除。本适配不验证实际音频播放，不能作为 HarmonyOS PC 本地播放器使用。目标 ELF 的 test_package 运行验证交由 CI；本地 noexec 环境不执行目标 ELF。
