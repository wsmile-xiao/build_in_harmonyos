# libheif-svtenc

libheif 的 **SVT-AV1（AV1）编码后端插件模块**。本包交付上游 libheif 1.23.0 树内的 CMake
目标 `heif-svtenc`（产物 `libheif-svtenc.so`），以及它运行所必需的宿主
`libheif.so`（`ENABLE_PLUGIN_LOADING=ON`）与包内树构建的 SVT-AV1 运行时
`libSvtAv1Enc.so`。

## 功能概述

- 在 libheif 中提供 **AV1 静图编码**能力（`heif_compression_AV1`），实现文件是上游树内的
  `libheif/plugins/encoder_svt.cc`；
- 插件以独立 `MODULE` 形态安装到 `<libdir>/libheif/`，由宿主在 `heif_init()` 时 `dlopen`
  并注册编码器（`heif_have_encoder_for_format(heif_compression_AV1) == 1`）；
- 同时交付宿主 `libheif.so`：仓库既有的 `libheif/1.22.2` 是 `ENABLE_PLUGIN_LOADING=OFF`
  的 codec-free 核心，运行期根本不装载插件，因此不能作为本包依赖。

## OHOS 适配

- **构建系统**：CMake（父 tarball）+ 包内树构建的 SVT-AV1（同为 CMake）。
- **唯一补丁**：`patches/0001-svt-av1-3.1.2-ohos-no-thread-affinity.patch`，作用于包内树
  构建的 SVT-AV1 3.1.2（**不改父 tarball 一行**）。内容与仓库既有归档
  `archives/l/libSvtAv1Enc/3.1.2/patches/0001-Source-Lib-Codec-svt_threads.h.patch` 逐字节
  一致：`Source/Lib/Codec/svt_threads.h` 的 `EB_CREATE_THREAD` 在 `__linux__` 分支调用
  `pthread_setaffinity_np()`，OHOS 的工具链虽然定义 `__linux__` 但不提供该函数，补丁把
  `__OHOS__` 排除到"不设线程亲和"的分支。
- **aarch64 优化**：SVT-AV1 在 aarch64 走 NEON 路径（configure 实测
  `HAVE_ARM_PLATFORM - Success`、`NEON_FLAG_SUPPORTED - Success`），不需要 NASM。
- **插件目录可移植性**：上游把默认插件目录编译期钉死（`heif_version.h` 的
  `LIBHEIF_PLUGIN_DIRECTORY` = 构建时的 `<prefix>/lib/libheif`，即 Conan 缓存里的绝对
  路径），跨缓存/跨机不可移植。本包用 `package_info()` 的 `runenv_info` 导出
  `LIBHEIF_PLUGIN_PATH`（上游 `libheif/plugins_unix.cc:37` 优先读该变量）解决。
- **无 `packaging/`**：按 ARCHIVE-SPEC v3.0，`packaging/` 已废弃，本包不创建。
- **无命令行工具**：`BUILD_APPS=OFF`，不构建 `SvtAv1EncApp`，故无 `commands.json`（R38）。

## 依赖关系

- **编译期**：无 Conan 依赖。SVT-AV1 本体在包内树构建（官方 v3.1.2 源码）。
- **运行期**：本包自带 `libSvtAv1Enc.so`（插件 `DT_NEEDED`）且随宿主一起装载；
  消费者只需 `conan install` 本包并用 `conanrun` 环境运行，`LIBHEIF_PLUGIN_PATH` 与
  `LD_LIBRARY_PATH` 会由 VirtualRunEnv 自动带上。
- 为什么没有把 SVT-AV1 写成 Conan 依赖：制品仓没有任何 `svt-av1`/`libSvtAv1Enc` 包
  （W0 实测，见版本级 notes.md「W0 依赖判定」），而 R36 是机械门禁
  （`finish` step[5/10] 与 CI L0i 对 `requires()` 逐条 `conan download --only-recipe`）。
  该形态在本仓库有已合并先例：`archives/h/handbrake/1.11.2/conanfile.py` 的 contribs
  （含 svt-av1）同样是内树构建、无 Conan 包依赖。

## 参考资料

- libheif 上游：<https://github.com/strukturag/libheif>
- SVT-AV1 上游：<https://gitlab.com/AOMediaCodec/SVT-AV1>
- 本仓库既有归档：`archives/l/libheif/1.22.2`（codec-free 核心）、
  `archives/l/libSvtAv1Enc/3.1.2`、`archives/s/svt-av1/4.1.0`、`archives/h/handbrake/1.11.2`
