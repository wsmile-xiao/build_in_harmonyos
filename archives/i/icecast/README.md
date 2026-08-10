# icecast

Icecast 是自由开源的流媒体服务器，支持 Ogg Vorbis/Theora、MP3、AAC、Opus 等格式的互联网电台广播。

## HarmonyOS PC adaptation

- 使用 autotools（configure/make）VPATH 构建，依赖从 Conan 包缓存解析（libxml2/2.15.3、libxslt/1.1.45.1、libvorbis/1.3.7 + libogg/1.3.6、curl/8.15.0、openssl/3.5.6.1、zlib/1.3.1.1）。
- 4 个 OHOS 补丁：config.guess/config.sub 增加 HarmonyOS 三元组识别（E007）；configure umask 077 改为 022 解决 HMDFS config.status 临时目录 Permission denied（E129）；src/thread/thread.c 以 __OHOS__ 守卫 pthread_setcancelstate（E085/E127）。
- 依赖 libdir 以 RPATH 嵌入二进制，configure 的 AC_RUN_IFELSE（libcurl 探测）与最终二进制均可裸跑（L2 smoke 通过）。
- libtheora/speex 为可选依赖且 OHOS 上未启用（configure WARN 级），不影响核心流媒体功能。
- 功能验证：`icecast --version` 输出 "Icecast 2.4.4"；最小配置启动后 `curl http://127.0.0.1:<port>/status.xsl` 返回 HTTP 200 + 完整 XSLT 渲染 XML，SIGTERM 干净关闭、端口释放。

## Consumer verification

Conan test_package 执行三项实质验证（R34）：版本冒烟（icecast --version）、服务器功能（最小配置启动 + /status.xsl 返回 XML，XSLT 渲染正常）、干净关闭（SIGTERM 各线程 shutdown 完整、端口释放）。HarmonyOS PC 上全部通过（conan-verify G0-G4/L2/L4/L5 PASS）。

## Reference

- https://icecast.org
- https://downloads.xiph.org/releases/icecast/
