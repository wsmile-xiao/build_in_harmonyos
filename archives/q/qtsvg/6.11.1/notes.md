# qtsvg 6.11.1 编译笔记

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
qtsvg 作为 Qt 子模块，直接依赖 qtbase。qtbase 已完成 HarmonyOS 适配后，qtsvg 编译无需额外补丁或源码修改。

### init-build 构建系统误判
init-build 将 qtsvg 误判为 autotools 构建系统，实际为 CMake 项目。手动使用 cmake 构建成功完成。

## 产物
- libQt6Svg.so.6.11.1 — SVG 渲染库
- libQt6SvgWidgets.so.6.11.1 — SVG Widget 库
- QtSvg/QtSvgWidgets 头文件
- CMake 配置文件 (Qt6Svg, Qt6SvgWidgets)
- pkg-config 文件 (Qt6Svg.pc, Qt6SvgWidgets.pc)

## 预编译包
- qtsvg-6.11.1-ohos-aarch64.tar.gz (38MB)
- qtsvg-6.11.1-ohos-aarch64-debug.tar.gz (7.8MB)

## 补丁文件
无补丁文件（编译无需源码修改）

**编译结束**: 2026-05-26 00:24
**最终状态**: built
---

**编译结束**: 2026-05-26 17:05
**最终状态**: built
