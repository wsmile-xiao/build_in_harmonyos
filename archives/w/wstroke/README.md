# wstroke

Port of [easystroke](https://github.com/thjaeger/easystroke) mouse gestures as a plugin for [Wayfire](https://github.com/WayfireWM/wayfire). Mouse gestures are shapes drawn while holding a mouse button and can be bound to window actions, key presses, commands, etc.

- **上游**: https://github.com/dkondor/wstroke (ISC, tag v2.4.0)
- **构建系统**: meson (上游), 手动 clang 构建核心用于 OHOS
- **分类**: gfx / utility

## 功能概述
- 手势绘制与识别 (stroke 引擎, 基于 easystroke)
- Wayfire 插件 (wstroke shared_module) 与 GTK 配置工具 (wstroke-config)
- 支持 EGL/Vulkan/pixman 渲染后端绘制笔迹

## OHOS 适配要点
- Wayfire / wlroots / wayland-server / gtkmm / vala 栈在 HarmonyOS PC 上不可用，完整插件无法构建
- 本适配仅提取可移植的 `stroke.c` / `stroke.h` 手势核心，以静态库 `libwstroke.a` 交付，保留算法能力
- 无上游测试套件 (meson 无 test 定义)，通过 `test_package` 的 4 个 stroke API 单元测试验证
- 源码下载通过 gh-proxy 镜像 + 官方 URL 双 fallback 保证 CI 稳定性

## 依赖
- 运行时: 仅 libc + libm
- 构建时: clang 15

## 参考
- 上游 README: https://github.com/dkondor/wstroke#readme
- 2.4.0 变更: 支持 Vulkan/pixman 渲染，依赖 Wayfire 0.10.0 + wlroots 0.19
