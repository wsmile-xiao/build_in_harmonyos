# unpaper

扫描纸张的后期处理工具，专为书籍页面（尤其是影印件扫描）设计：自动去歪斜
(deskew)、裁剪边距、黑白化、去噪、遮罩与方向校正等。

- 上游仓库：https://github.com/unpaper/unpaper
- 许可证：GPL-2.0-only

## HarmonyOS PC 适配（7.0.0）

unpaper 7.0.0 通过 FFmpeg 的 libavformat/libavcodec/libavutil 读写
PBM/PPM/PGM/PNG 图像。HarmonyOS PC 既无 FFmpeg 的 conan 包，也无系统库，
故本配方从官方 FFmpeg 8.1.2 源码内联构建一套最小静态库（仅 ppm/pgm/pbm/png/
rawvideo 编解码 + image2 容器 + file 协议 + zlib），再直接编译 unpaper 的
5 个 C 源（与上游 meson.build 同源同标志）并静态链接为单一 `unpaper` 可执行文件。

上游 Meson 构建（依赖 sphinx-build 生成手册、pytest+PIL 跑金标图像测试）在
OHOS worker 上不可用，故被绕过；test_package 以 `unpaper --version` 与一次
PPM 图像往返验证读写链路。

详见 `7.0.0/notes.md`。
