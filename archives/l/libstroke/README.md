# libstroke

libstroke 是一个轻量级 C 手势笔画识别库，可将二维采样点序列转换为九宫格方向数字序列。

## 功能概述

- 记录鼠标、触控笔或触摸输入产生的二维坐标点。
- 对采样轨迹进行插值、缩放与九宫格量化。
- 输出可供应用程序匹配的紧凑笔画序列。
- 可选的 X11 轨迹显示接口由上游提供，但不是核心识别 API 的依赖。

## OHOS 适配

- 使用 Conan 配方直接调用 OHOS Clang 编译核心 `libstroke` C 源码，避免旧版 Autotools 配置脚本强制探测 X11。
- 应用一个通用 C 语言可移植性补丁，补充 `strcpy` 所需的标准头文件。
- 默认生成静态库；核心识别接口在 HarmonyOS PC arm64 真机上完成链接与运行验证。
- 上游可选的 GTK 1.x `libgstroke` 包装和 Java 演示不属于核心 `libstroke` 包。

## 依赖关系

- 编译依赖：OHOS Clang、LLVM ar、Conan 2.x。
- 运行依赖：HarmonyOS C 运行库和系统数学库 `libm`。
- 第三方依赖：无。

## 参考资料

- 上游主页：https://www.etla.net/libstroke/
- 源码镜像：https://ftp.rrze.uni-erlangen.de/gentoo/distfiles/cc/libstroke-0.5.1.tar.gz
