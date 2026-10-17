# libminc 2.5.0 — OHOS (aarch64) 适配笔记

## 上游与源码

- 上游：BIC-MNI/libminc（MINC 医学影像格式库；MINC1=netCDF 底层，MINC2=HDF5 底层）
- 版本：2.5.0（tag `release-2.5.0`）
- 源 URL：`https://github.com/BIC-MNI/libminc/archive/refs/tags/release-2.5.0.tar.gz`
  - sha256 `57d807e86a353a93024a8849f5e21e2abea4f09f0be934e1f538bdc2b02f8885`
  - 选型依据：search-url 给出的 savannah/zlib.net/waterlan 候选实测全是 404 页或
    Not Found（§5.1 假阳性形态，371B HTML / 9B "Not Found"）；GitHub 官方 tag
    archive 下载校验通过后采用（单值 URL，sha256 锚定）。
  - Debian pool 同版本 orig.tar.gz（sha256 `1335c7ee…`）内容等价但为发行版重打包，
    优先官方 archive。

## 依赖（ohpcd 已发行，W0 实装验证）

| 依赖 | 版本 | 说明 |
|---|---|---|
| hdf5 | 1.14.6 | MINC2 底层；包内静态链 zlib（DT_NEEDED 无 libz，实测） |
| netcdf | 4.9.3 | MINC1 底层；同样静态链 zlib |
| zlib | 1.3.1.1 | 静态变体（libz.a）；与 hdf5/netcdf 的链入形态一致 |

版本冲突教训：显式指定 zlib/1.3.1 会与 hdf5 的 zlib/1.3.1.1 冲突
（`Version conflict`），交给依赖图解析（或对齐 1.3.1.1）。

## 配方关键决策

1. **模块模式 find_package 对接**（详见 knowledge/drafts/E632-*.md）：
   上游全用模块模式（`find_package(ZLIB)`、`HDF5_NO_FIND_PACKAGE_CONFIG_FILE=ON` +
   `find_package(HDF5 COMPONENTS C)`、上游自带 FindNETCDF.cmake）。CMakeToolchain
   恒定 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`，CMakeDeps config 抢跑后只给扁平
   target、不给上游消费的大写变量。处置：三依赖 `cmake_find_mode=none` +
   `tc.variables` 预设 `ZLIB_LIBRARY/ZLIB_INCLUDE_DIR/NETCDF_LIBRARY/
   NETCDF_INCLUDE_DIR/HDF5_ROOT` + `-I/-L` 全量注入兜底。
2. **OHOS 平台块**（libmatio/netcdf 同型）：`cmake_system_name=OHOS` +
   `cmake_system_processor=aarch64`。不设则平台文件名 HarmonyOS 对不上，
   `if(UNIX)` 分支（-lm/-ldl、soversion 规则）整体不生效。
3. **LIBMINC_MINC1_SUPPORT=ON**：MINC1 格式（netcdf 底层）是 MINC 生态核心遗留
   格式，依赖已在架，全功能发行（Debian 同开）。关掉它 libminc 只剩 MINC2 一半功能。
4. **LIBMINC_BUILD_EZMINC=OFF**：ezminc 是 C++ 便利封装层（非核心格式能力），
   首版为最小化适配面关闭；需要它的下游可用 `find_package` 直接消费 C 库自建封装。
   **LIBMINC_USE_NIFTI=OFF**：上游 ON 时走 ExternalProject 构建期外网拉取 nifti
   源码，不可复现。
5. `LIBMINC_BUILD_SHARED_LIBS` 跟随 options.shared（默认 shared=True）；
   hdf5/netcdf 动静态对齐 shared=True。
6. 上游默认静态（LIBMINC_BUILD_SHARED_LIBS OFF），conan 配方显式传 `ON/OFF`。
7. **CMAKE_SKIP_RPATH=ON（ELF 零改写，原生签名）**：上游给 minc2 设了
   `INSTALL_RPATH`，CMake install 的 RPATH 改写必改 .dynstr（SKIP_INSTALL_RPATH
   也只是清零，实测 143 字节），hnp 产物的 .codesign 链接器签名随之失效，
   加载报 `Error loading shared library ... Permission denied`；判据=包副本与
   build-tree 副本 sha256 对比（实测改写后不一致、SKIP_RPATH 后一致
   b686497eaf1e65c49b45c0d31431c9005f7eed904d0a04381d780c5cd26f8048）。
   本包因此**不走** libmatio/netcdf 的 `_sign_binaries()` 重签惯例——零改写下
   原生签名完好。产物无 RUNPATH，依赖由消费方 conanrun/rpath 提供（与仓内其他
   包的下游用法一致）。
8. **测试补丁 0001-testdir-mincapi.c.patch**：musl（OHOS）未播种 `rand()` 首值
   恒为 0（实测；glibc 首值 1804289383），上游 mincapi test4 的
   `miicv_detach(rand())`（期望非法 id 被拒绝）命中合法 ICV id 0（槽 0，
   MI_MAX_NUM_ICV=1000）意外成功计 error。补丁强制 id ≥2^30（恒高于槽位上限），
   平台无关保持测试意图。glibc 下 `rand()|0x40000000` 同样恒高于上限，行为不变。

## 已知边界

- 上游 ctest 套件（`testdir/`）随配方 `build()` 的 `cmake.test()` 真跑；
  `test_package` 另做 MINC2+MINC1 双链路消费者断言（`H5Fis_hdf5`/`ncinq`
  底层指纹，证明两个依赖真接上）。
- 上游 `check_clock_gettime` 有 try_run 分支（交叉编译下 try_run 无法运行目标
  二进制），仅影响 config.h 的 `HAVE_CLOCK_GETTIME` 声明，不影响链接
  （musl 的 clock_gettime 在 libc 内）；若 CHECK_LIBRARY_EXISTS(rt ...) 命中
  则根本不走该分支。
- 版本字符串注意：上游 `LIBMINC_PACKAGE_VERSION_PATCH` 是 `01`，自报版本为
  `2.5.01`（历史如此，非本配方引入）。
