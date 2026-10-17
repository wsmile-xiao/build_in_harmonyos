# gxr

gxr 是 xrdesktop 使用的 GLib/GObject XR 抽象库，为 OpenXR 与 OpenVR 后端提供统一的上下文、动作、设备、覆盖层和 Vulkan 渲染接口。

## 功能概述

- XR 上下文、会话和设备生命周期管理
- 动作集、动作清单与控制器绑定
- Vulkan 覆盖层、指针、模型和帧缓冲辅助接口
- GLib 资源与缓存路径 IO
- C API 与 C++ 消费兼容

## OHOS 适配要点

- 使用 Conan 2 与 Meson 构建 OHOS AArch64 共享/静态库。
- 使用制品仓中的 gulkan、GTK、GLib、JSON-GLib 与 HarfBuzz 依赖，不捆绑其他项目源码。
- 在 Linux 交叉环境中验证构建机工具可执行性，避免误用 AArch64 `pkgconf`/`glslangValidator`。
- HarmonyOS 不构建依赖 X11 头与 XTest 的键盘合成示例；其他核心库、示例和四个上游测试目标保持编译覆盖。
- OpenXR 路径补齐 Vulkan 扩展协商和运行时物理设备验证，并在 Monado 模拟 HMD + llvmpipe 环境完成全部上游测试。

## 版本

- 0.15.1（2026-09-09）— OHOS AArch64 Conan 迁移，共享/静态构建及全部本地验证通过。

## 参考资料

- 上游：https://gitlab.freedesktop.org/xrdesktop/gxr
- 适配记录：`0.15.1/notes.md`
