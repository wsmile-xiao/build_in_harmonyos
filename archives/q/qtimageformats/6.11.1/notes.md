# qtimageformats 6.11.1 编译笔记

## 编译日期
2026-05-26

## 编译环境
- 系统: HarmonyOS (HongMeng Kernel 1.12.0)
- 编译器: clang 15.0.4
- 链接器: GNU ld 2.45
- 构建系统: CMake 4.1.2

## 依赖
- qtbase 6.11.1 ✅

## 问题与解决

### 无需源码修改
qtimageformats 作为 Qt 子模块，直接依赖 qtbase。qtbase 已完成 HarmonyOS 适配后，qtimageformats 编译无需额外补丁或源码修改。

## 产物
- libqtga.so — TGA 图像格式插件
- libqwbmp.so — WBMP 图像格式插件
- libqtiff.so — TIFF 图像格式插件
- libqwebp.so — WebP 图像格式插件
- libqicns.so — ICNS 图像格式插件
- CMake 配置文件 (Qt6QTgaPlugin, Qt6QWbmpPlugin, Qt6QTiffPlugin, Qt6QWebpPlugin, Qt6QICNSPlugin)
- FindLibmng.cmake, FindWrapJasper.cmake, FindWrapWebP.cmake
- qtimageformats-6.11.1.spdx (SBOM)

## 预编译包
- qtimageformats-6.11.1-ohos-aarch64.tar.gz (730K)
- qtimageformats-6.11.1-ohos-aarch64-debug.tar.gz (880K)

## 补丁文件
无补丁文件（编译无需源码修改）

**编译结束**: 2026-05-26 10:04
**最终状态**: built