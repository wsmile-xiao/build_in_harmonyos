# simage 1.8.4 — HarmonyOS PC 适配笔记

## 概述

simage（Coin3D simage）是 Coin3D 的图像文件格式抽象层（C 库），支持 JPEG/PNG/TIFF/GIF/RGB/PIC/TGA/EPS 等图像格式及 AVI/MPEG 视频、Ogg/Vorbis 音频（通过外部库）。本包基于上游 [coin3d/simage](https://github.com/coin3d/simage) tag v1.8.4（commit 0c93effb，2025-06-29，ISC 许可）。

## 适配策略

- **构建系统**：CMake 3.5+，原生构建（build=target=OHOS aarch64），通过 OHOS NDK `ohos.toolchain.cmake` 自发现（与 in-tree coin/sail/libtiff 同法），直接 `self.run('cmake -B ...')` 驱动系统 cmake，避免 Conan CMake()/CMakeToolchain 注入的 conancenter `cmake/<ver>` tool_requires 在 os=OHOS 构建上下文下 `KeyError: 'OHOS'`。
- **Codec 选项**：为保持依赖图为空（零外部 conan requires），关闭所有需要外部三方库的格式：
  - `SIMAGE_ZLIB_SUPPORT=OFF`（zlib）
  - `SIMAGE_GIF_SUPPORT=OFF`（giflib）
  - `SIMAGE_JPEG_SUPPORT=OFF`（libjpeg）
  - `SIMAGE_PNG_SUPPORT=OFF`（libpng+zlib）
  - `SIMAGE_TIFF_SUPPORT=OFF`（libtiff）
  - `SIMAGE_LIBJASPER_SUPPORT=OFF`、`SIMAGE_LIBSNDFILE_SUPPORT=OFF`、`SIMAGE_OGGVORBIS_SUPPORT=OFF`（jasper/libsndfile/oggvorbis）
  - `SIMAGE_XWD_SUPPORT=OFF`（experimental）
  - 保留自包含 codec：`SIMAGE_RGB_SUPPORT=ON`、`SIMAGE_PIC_SUPPORT=ON`、`SIMAGE_TGA_SUPPORT=ON`、`SIMAGE_EPS_SUPPORT=ON`、`SIMAGE_MPEG2ENC_SUPPORT=ON`（mpeg2enc 源码内嵌）。
- **库类型**：默认静态 (`shared=False`)，避免共享库在 OHOS 上的代码签名要求；`shared=True` 时 package() 内对 lib/*.so* 执行 llvm-objcopy + binary-sign-tool 自签（与 coin 同法）。
- **上游测试**：`SIMAGE_BUILD_TESTS=ON` 启用 CTest 单用例 `loaders`（tests/loaders.c），对 tests/ 目录下 8 张图片（img.gif/jpg/png/rgb/tga/tif + small_img.*）调用 `simage_check_supported` / `simage_read_image`；loaders 对不支持格式仅打印 "not in a supported format" 不报错，因此关闭外部 codec 后仍 PASS。

## 上游测试

- **测试框架**：CTest（CMake `enable_testing()` + `add_test(loaders ...)`），测试二进制内部无额外框架，直接遍历文件并打印结果，ctest 汇总行形如 `100% tests passed, 0 tests failed out of 1`。
- **统计口径**：`ctest_entries`（CMake 注册的 ctest 用例数），`upstream_test_total=1`（loaders 单测），由 `ctest -N` 与 `ctest --output-on-failure` 汇总行双重确认。
- **执行方式**：conanfile.py `build()` 内 `cmake --build` 后运行 `ctest --output-on-failure`，以单一确定性来源（汇总行正则 `(\d+) tests failed out of (\d+)`）解析 discovered/failed，`passed=discovered-failed-skipped`，写入 `build_folder/upstream_test_summary.json` 并在 `package()` 拷入 `res/`，test_package 阶段复发 `HMBS_UPSTREAM_TEST_RESULT`（hmbs 仅扫描 test_package 阶段 stdout，缓存命中跳过 build() 时证据不丢）。
- **本地验证**：待 hmbs 真机（ohos@c1:20222）执行 `conan create` 预检，以真实 ctest 输出为准；当前声明 `upstream_tests_exist: true`，`upstream_test_total: 1`，`upstream_test_count_method: ctest_entries`。

## test_package

`test_package/test_simage.c` 三个真实用例（均调用 simage API）：

1. `simage_version()` 校验主版本 =1、次版本=8、微版本=4 且合成 version 字符串 "1.8.4"；
2. `simage_check_supported()` 对内置格式 `test.rgb` 判支持（=1）、对未知扩展 `test.unsupported_xyz` 判不支持（=0），并校验 `simage_next_power_of_two(300)==512`；
3. `simage_resize()` 对 2x2 RGB 图像缩至 1x1 并校验返回非空且可 free。

真实断言完成后打印 `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_simage","discovered":3,"passedCount":3}`（数字来自真实计数，无字符串数数/减法推导/修正分支）。

## 产物布局

```
lib/libsimage.a                # 静态库（shared 时为 libsimage.so*）
lib/pkgconfig/simage.pc        # pkg-config（-lsimage -lm，prefix 相对化）
lib/cmake/simage-1.8.4/*       # simage-config.cmake / simage-config-version.cmake / simage-export.cmake（find_package(simage)）
include/simage.h               # 主头文件（C API）
res/upstream_test_summary.json # 上游 ctest summary（供 test_package 复发）
```

## 已知问题

- 外部 codec 关闭后，`simage_check_supported("img.png")` 等会返回 0（not supported），loaders 测试中这些图片对应行仅打印 not supported，不计为失败；如需 PNG/JPEG 等支持，需另行适配 libpng/libjpeg/giflib/libtiff 依赖并开启对应 SIMAGE_*_SUPPORT。
- 静态库无需签名；共享库已按 OHOS XPM 要求自签，若消费者在链接时报 "Error loading shared library"，检查是否未经签名或 LIBGL 变量缺失（与 simage 无关）。
