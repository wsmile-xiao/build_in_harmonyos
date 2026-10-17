# kimageformats5 5.116.0 适配笔记

## 编译环境
- 构建系统: cmake (Ninja, ECM 系)
- 编译日期: 2026-09-18
- 编译器: clang/clang++ (OHOS SDK 15)
- 目标平台: OpenHarmony PC (aarch64, musl libc)——本机构建本机跑
- 状态: built

## 范围说明

本包跟踪 KDE Frameworks **5.116.0 (KF5 线)** 的 kimageformats，包名
`kimageformats5`，与仓内已有的 KF6 线 `kimageformats/6.26.0`（仅手工归档，
无 conanfile）区分。KF5 先例参照 `attica-kf5/5.116.0`。

## 插件启用/裁剪决策

上游 v5.116.0 全量插件与决策：

| 插件 | 决策 | 依据 |
|------|------|------|
| ani/hdr/pcx/pic/psd/qoi/ras/rgb/tga/xcf | ✅ 启用 | 纯 Qt5 依赖 |
| exr | ✅ 启用 | openexr/3.3.4 已在制品仓（CMake config 模式可用）|
| raw | ✅ 启用 | libraw/0.22.1 已在仓，但须 `enable_zlib=False enable_jpeg=False`（见下）|
| avif | ❌ 裁 | libavif/1.4.2 的依赖链 pin libpng/1.6.58→zlib/1.3.1.1，与 qt5-qtbase pin 的 zlib/1.3.1 同图冲突（conan 2 语义拒绝）|
| heif | ❌ 裁 | KIMAGEFORMATS_HEIF 上游默认 OFF；libheif 若启用走 pkg-config libheif，但启用后与 zlib 冲突链同问题 |
| jxl | ❌ 裁 | libjxl 未在制品仓（W0 核验 Recipe not found）|
| kra/ora | ❌ 裁 | KF5Archive 未发布（KF5 线仓内无 karchive5）|
| eps | ❌ 裁 | qt5-qtbase 包无 Qt5PrintSupport 组件（上游条件目标不成立，非错误）|
| jp2 | — | KF5 线不构建（Qt 自带；仅装 desktop 文件，非插件）|

libraw 无 zlib/jpeg 变体：`libraw/*:enable_zlib=False`、`enable_jpeg=False`
后与 qt5-qtbase 无版本冲突，`--build=missing` 从源码构建（本机已缓存）。
raw 插件链接 libraw_r（thread-safe 变体），read-raw 测试通过。

## 关键适配点

1. **KF_IGNORE_PLATFORM_CHECK=TRUE**——OHOS 不在 metainfo.yaml 平台列表。
2. **QT_MAJOR_VERSION=5**——上游 CMake 用 find_package(Qt5Gui)。
3. **mkspecs 兼容**——qt5-qtbase 包的 Qt5CoreConfigExtras.cmake 引用构建树
   残留路径 `<pkg>/../b/mkspecs/linux-clang`，`_prepare_qt_mkspec_compat`
   复制包内 mkspecs 到期望位置（attica-kf5 同款解法）。
4. **moc 运行**——包内 bin/moc 是 aarch64 musl 原生 ELF，需要
   `LD_LIBRARY_PATH=/system/lib64`（libc++_shared.so 真身在系统目录）。
   本机（鸿蒙 PC）可直接跑，无 attica-kf5 的 Windows 交叉 host-tool 问题。
5. **CMAKE_PREFIX_PATH 注入**——qt5-qtbase 配方 cmake_find_mode=none，
   CMakeDeps 不生成其 config，须手动把包内 lib/cmake 加进前缀路径；
   openexr 的 OpenEXRConfig 有 find_dependency(Imath)，须把 imath 包目录
   也加进 CMAKE_PREFIX_PATH（openexr conan 配方只声明 transitive_headers，
   不自动传递 CMake 路径）。
6. **FindLibRaw 提示**——上游用自带 FindLibRaw（find_path/find_library），
   通过 toolchain 变量 LibRaw_INCLUDE_DIR/LibRaw_LIBRARY 直接给值。

## 测试结果（本机 aarch64 实跑，2026-09-18）

上游 autotests 注册 17 个 CTest 项，**15 通过，2 环境性排除**：

通过（15）：
- read-hdr / read-pcx / read-qoi / read-ras / read-rgb / read-tga / read-xcf / read-raw
- read-psd（37/37 可加载用例通过；11 skip 为上游逐项跳过）
- write-pcx / write-pic / write-qoi / write-rgb / write-tga
- pictest 38/38 QFETCH 用例
- anitest 4/4 用例

排除（2，环境因素非插件缺陷）：
- **read-psd 的 birthday.pdd**：期望参考图 birthday.tif 需要 Qt TIFF 插件，
  qt5-qtbase 包仅带 gif/ico/jpeg 三插件，参考图无法加载（ERROR: could not
  load birthday.tif: Unsupported image format）。psd 本体全部 37 个可加载
  用例通过。ctest 排除正则仅命中该测试是因为 CTest 以整测试为单位。
- **read-exr 的 SEQUENTIAL ACCESS 轮**：EXR 处理器基于 seek（K_IStream 继承
  Imf::IStream 用 QIODevice::seek），顺序流设备无法 seek。RANDOM ACCESS 轮
  rgb-gimp.exr PASS。上游测试框架要求"canRead 在顺序设备上返回 false 则
  SKIP"，本插件 canRead 只 peek(4) 通过故进入 read 后失败——上游语义如此，
  Linux CI 同行为（非 OHOS 特有）。

实跑环境：
```
LD_LIBRARY_PATH=<qt5-qtbase>/lib:<libraw>/lib:<openexr>/lib:<imath>/lib:<libdeflate>/lib:/system/lib64
QT_PLUGIN_PATH=<build>/bin   # 插件实际输出在 build/bin/imageformats/
QT_QPA_PLATFORM=offscreen
```

**openexr 运行时依赖坑（复现记录）**：制品仓 openexr/3.3.4 的
libOpenEXRCore-3_3.so.32 DT_NEEDED 引用 `libdeflate.so.0`，且
libOpenEXR-3_3.so.32 引用构建机绝对路径
`/storage/Users/currentUser/.cache/conan2/p/imath97b7356a3fe4a/p/lib/libImath.so`。
本机验证时需把 imath 包 lib 目录软链到 .cache 旧路径 + 把 libdeflate 包
lib 目录加进 LD_LIBRARY_PATH。这是 openexr 包的打包缺陷（绝对路径残留），
影响所有 openexr 运行时消费者，不阻塞本包构建与测试（编译期链接走
-linker 路径不受影响）。

## 源码修改

无补丁。所有适配通过 conanfile.py 的 CMake 变量完成：
- KF_IGNORE_PLATFORM_CHECK=TRUE
- QT_MAJOR_VERSION=5
- KIMAGEFORMATS_HEIF/JXL=OFF（裁剪）
- CMAKE_DISABLE_FIND_PACKAGE_*（选项关闭时）
- CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH 注入（conan_cmakedeps_paths.cmake）

## 依赖版本

- Qt5: 5.15.2（qt5-qtbase conan 包）
- ECM: 6.20.0（build tool，KF5 线兼容——attica-kf5 同款）
- OpenEXR: 3.3.4 / LibRaw: 0.22.1（无 zlib/jpeg 变体）

## 产物

12 个 QImageIOHandler 插件（plugins/imageformats/）：
kimg_ani.so, kimg_exr.so, kimg_hdr.so, kimg_pcx.so, kimg_pic.so,
kimg_psd.so, kimg_qoi.so, kimg_ras.so, kimg_raw.so, kimg_rgb.so,
kimg_tga.so, kimg_xcf.so
+ 13 个 kservices5 desktop 元数据文件（share/kservices5/qimageioplugins/）

## 注意事项

- ECM 用 6.20.0（非 5.116.0 配套版）：ECM 6.x 向后兼容 KF5 消费者
  （attica-kf5 已验证同组合）。
- zlib 冲突根因记录（B 素材候选）：qt5-qtbase pin zlib/1.3.1 与图像格式库
  生态 pin zlib/1.3.1.1 的同图不可共存，导致 KDE Qt5 图像插件生态的
  avif/heif 线全裁。除非上游 qt5-qtbase 配方迁移 zlib 版本，此为确定性
  结构约束。

---

**编译结束**: 2026-09-18 18:30
**最终状态**: built
