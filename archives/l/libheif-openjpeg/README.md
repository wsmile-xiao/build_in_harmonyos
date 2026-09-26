# libheif-openjpeg

libheif 的 **OpenJPEG（JPEG 2000）编解码后端插件模块**，从 libheif 官方源码树的
`libheif/plugins/{decoder,encoder}_openjpeg.cc` 编译而来——即上游 CMake 目标
`heif-j2kdec` / `heif-j2kenc` 的产物 `libheif-j2kdec.so` / `libheif-j2kenc.so`。

## 描述

libheif 把编解码后端设计成**可独立装载的插件**：宿主库 `libheif.so` 在
`heif_init()` 时 `dlopen` 插件目录下的模块并注册后端。本包交付：

| 产物 | 位置 | 说明 |
|------|------|------|
| `libheif-j2kdec.so` | `lib/libheif/` | **本包命名产物之一**：JPEG 2000 解码后端插件模块 |
| `libheif-j2kenc.so` | `lib/libheif/` | **本包命名产物之一**：JPEG 2000 编码后端插件模块 |
| `libheif.so` | `lib/` | 宿主库（同源同版本 1.23.0，`ENABLE_PLUGIN_LOADING=ON`）——插件无法脱离它运行 |
| `libheif/*.h` | `include/` | 公共头文件（含 `heif_version.h`） |
| `libheif.pc` / `libheif-config*.cmake` | `lib/pkgconfig`、`lib/cmake/libheif` | 供 pkg-config / CMake 消费 |

上游的 OpenJPEG 后端默认既不开编码也不开解码（`plugin_option(OpenJPEG_ENCODER/DECODER … OFF ON)`）；
本包通过 `WITH_OpenJPEG_{DECODER,ENCODER}=ON` + `WITH_OpenJPEG_{DECODER,ENCODER}_PLUGIN=ON`
+ `ENABLE_PLUGIN_LOADING=ON` 把它构建为两个独立 MODULE（这正是包名对应的产物）。

## 功能概述

* JPEG 2000 解码后端：让 libheif 能解码 HEIF/HEIC 中的 J2K（`j2k1`）图像项；
* JPEG 2000 编码后端：让 `heif_context_get_encoder_for_format(heif_compression_JPEG2000)`
  可取到编码器；
* 以插件模块形态交付，宿主与后端可分别升级；
* 其余编解码后端（libde265/x265/aom/dav1d/x264/kvazaar/uvg266/vvdec/vvenc/openjph/
  ffmpeg/openh264/rav1e/svt/jpeg/未压缩编码/WebCodecs）在本包中**全部关闭**，
  它们是兄弟包（如 libheif-libde265、libheif-aom…）的交付面。

## OHOS 适配

* 依赖仓库既有独立包 `openjpeg/2.5.4`（不内树重建）。该包 manifest `status: built`，
  远端 ohpcd 有 binary；仓库内 5 个已合并包在用（imagemagick-full/leptonica/opencv/poppler/openslide）。
* **CMakeDeps 接线（本族最容易踩的假绿点）**：libheif 的 `plugin_compilation()` 用
  **全大写** `OPENJPEG_FOUND`/`OPENJPEG_LIBRARIES`/`OPENJPEG_INCLUDE_DIRS` 判后端是否存在，
  而 CMakeDeps 在 config 模式只 set `OpenJPEG_*`，且 CMakeToolchain 默认
  `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON` → 不显式处理就会 `Not compiling 'j2kdec' backend`
  却全程 rc=0（包能建出来、没有插件）。本包在 `generate()` 里设
  `cmake_find_mode="module"` + `cmake_additional_variables_prefixes=["OPENJPEG"]` 解决。
* **C++20 ranges（编译期硬阻塞）**：libheif 1.23.0 的 `box.cc` 用
  `std::ranges::all_of/find`；OHOS SDK libc++ 15004 在未定义 `_LIBCPP_ENABLE_EXPERIMENTAL`
  时定义 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES`，把这两个算法藏起来 → 编译失败。
  本包在 `generate()` 里对 OHOS 加 `tc.preprocessor_definitions["_LIBCPP_ENABLE_EXPERIMENTAL"] = None`，
  **上游源码零修改、无补丁**（同族先例 libpqxx/8.0.1、cdo/2.6.3、mrc/1.3.17）。
  公共 API 头 0 处 `std::ranges` → 不需要向消费者传播该宏。
* **插件目录运行期口径（已知限制）**：上游把默认插件目录编译期钉死为构建时的绝对路径
  （`heif_version.h` 的 `LIBHEIF_PLUGIN_DIRECTORY`，即 Conan 包目录），跨缓存/跨机不可移植。
  消费方须让 `LIBHEIF_PLUGIN_PATH` 指向本包的 `lib/libheif`（本包已用 `package_info()` 的
  `runenv_info` 导出，`conanrun` 环境 / `VirtualRunEnv` 自动生效）；变量名是**单数**
  `LIBHEIF_PLUGIN_PATH`（上游 `plugins_unix.cc` 实现口径）。
* 与 `libheif/1.22.2` 的关系：后者是 `ENABLE_PLUGIN_LOADING=OFF` 的 codec-free 核心；
  两者都提供 `libheif.so`（1.23.0 带插件装载 / 1.22.2 不带），同一消费者不要同时依赖。

## 依赖

| 类型 | 包 | 说明 |
|------|----|------|
| 编译依赖 | `openjpeg/2.5.4` | JPEG 2000 编解码库 `libopenjp2.so`，两个插件模块都链接它（DT_NEEDED 实测含 `libopenjp2.so.7`） |
| 运行期 | 宿主 `libheif.so` | 由本包自包含交付（同源同版本） |

## 上游测试

上游 `tests/`（父 tarball libheif 1.23.0）共 **217** 个 Catch2 `TEST_CASE`
注册点（全量注册面「用例/注册类」最大值口径，取数命令见版本目录 `notes.md` §5）；
父 tarball 内**没有 J2K 语料**，因此上游对 OpenJPEG 后端的直接覆盖是
`tests/encode_jpeg2000.cc` 的 2 个用例（真编码），解码方向由 `test_package` 的往返用例
（真编码 + 真解码 + 尺寸/保真度断言）承担。上游其余用例按 NOT_RUN 记账，
逐项归因见版本目录 `notes.md` §6。

## 参考资料

* 上游仓库: https://github.com/strukturag/libheif
* 插件机制源码: `libheif/plugins/CMakeLists.txt`、`libheif/init.cc`、`libheif/plugins_unix.cc`
* 同族先例: `archives/l/libheif/1.22.2`（codec-free 宿主）、
  `archives/o/openjpeg/2.5.4`（JPEG 2000 编解码库）、
  `archives/l/libheif-tools/1.23.0`（**同一 libheif v1.23.0 tarball 的已合并先例**）、
  `archives/l/libhwy_contrib/1.3.0`（父 tarball 内子模块独立成包的已合并先例）
