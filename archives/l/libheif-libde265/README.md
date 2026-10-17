# libheif-libde265

libheif 的 **libde265（HEVC）解码后端插件模块**，从 libheif 官方源码树的
`libheif/plugins/decoder_libde265.cc` 编译而来——即上游 CMake 目标
`heif-libde265` 的产物 `libheif-libde265.so`。

## 描述

libheif 把编解码后端设计成**可独立装载的插件**：宿主库 `libheif.so` 在
`heif_init()` 时 `dlopen` 插件目录下的模块并注册后端。本包交付：

| 产物 | 位置 | 说明 |
|------|------|------|
| `libheif-libde265.so` | `lib/libheif/` | **本包命名产物**：HEVC 解码后端插件模块（静态链入 libde265） |
| `libheif.so` | `lib/` | 宿主库（同源同版本 1.23.0，`ENABLE_PLUGIN_LOADING=ON`）——插件无法脱离它运行 |
| `libheif/*.h` | `include/` | 公共头文件（含 `heif_version.h`） |
| `libheif.pc` / `libheif-config*.cmake` | `lib/pkgconfig`、`lib/cmake/libheif` | 供 pkg-config / CMake 消费 |

上游的 `libde265` 后端默认是「静态编入宿主」；本包通过
`WITH_LIBDE265=ON` + `WITH_LIBDE265_PLUGIN=ON` + `ENABLE_PLUGIN_LOADING=ON`
把它构建为独立 MODULE（这正是包名对应的产物）。

## 功能概述

* HEVC（H.265）解码后端：让 libheif 能解码 HEIC/HEIF 中的 HEVC 图像项；
* 以插件模块形态交付，宿主与后端可分别升级；
* 其余编解码后端（x265/aom/dav1d/x264/kvaarar/uvg266/vvdec/vvenc/openjpeg/
  openjph/ffmpeg/openh264/rav1e/svt/jpeg/未压缩编码）在本包中**全部关闭**，
  它们是兄弟包（如 libheif-x265、libheif-aom…）的交付面。

## OHOS 适配

* 依赖仓库既有独立包 `libde265/1.0.18`（不内树重建）。该包已解决
  **aarch64 NEON** 问题：`libde265/arm/*.S` 是 ARMv7-A NEON、在 aarch64 上不可
  汇编，故关 `HAVE_NEON`/`ENABLE_ARM` 走便携 C 回退。**NEON 加速路径在本包中未
  编译、未运行**（如实登记，不写 PASS）。
* libheif 1.23.0 使用了 C++20 ranges 算法（`all_of`/`find`）；OHOS SDK 的
  libc++ 15004（clang 15.0.4）声明 `__cpp_lib_ranges` 却未提供这些算法 →
  本包带 1 个可移植性补丁改为等价的 C++17 `std::all_of`/`std::find`。
* **插件目录运行期口径（已知限制）**：上游把默认插件目录编译期钉死为构建时的
  绝对路径（Conan 包目录），跨缓存/跨机不可移植。消费方须让
  `LIBHEIF_PLUGIN_PATH` 指向本包的 `lib/libheif`（本包已用 `package_info()` 的
  `runenv_info` 导出，`conanrun` 环境 / `VirtualRunEnv` 自动生效）；
  注意变量名是**单数** `LIBHEIF_PLUGIN_PATH`（上游 `plugins_unix.cc` 实现口径，
  `heif_library.h` 注释里的复数 `LIBHEIF_PLUGIN_PATHS` 是过期文档）。
* 与 `libheif/1.22.2` 的关系：后者是 `ENABLE_PLUGIN_LOADING=OFF` 的 codec-free
  核心；两者都提供 `libheif.so`（1.23.0 带插件装载 / 1.22.2 不带），
  同一消费者不要同时依赖。

## 依赖

| 类型 | 包 | 说明 |
|------|----|------|
| 编译依赖 | `libde265/1.0.18` | HEVC 解码库，静态链入插件模块（无额外运行期依赖） |
| 运行期 | 宿主 `libheif.so` | 由本包自包含交付（同源同版本） |

## 上游测试

上游 `tests/`（父 tarball libheif 1.23.0）共 **217** 个 Catch2 `TEST_CASE`
注册点（全量注册面最大值口径）；它们不在本包交付面（上游 `tests/` 无 `install()`
规则），本包按 `BUILD_TESTING=OFF` 构建，217 项按 NOT_RUN 记账，逐项归因见
版本目录 `notes.md` 第 5 节。消费者验证由 `test_package/` 的 9 项鸿蒙特有检查承担
（含"宿主 dlopen 本插件后 `heif_have_decoder_for_format(HEVC) == 1`"）。

## 参考资料

* 上游仓库: https://github.com/strukturag/libheif
* 插件机制源码: `libheif/plugins/CMakeLists.txt`、`libheif/init.cc`、`libheif/plugins_unix.cc`
* 同族先例: `archives/l/libheif/1.22.2`（codec-free 宿主）、
  `archives/l/libde265/1.0.18`（HEVC 解码库）、
  `archives/l/libhwy_test/1.3.0`（父 tarball 内子模块独立成包的同族先例）
