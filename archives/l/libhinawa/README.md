# libhinawa

libhinawa 是一个基于 GObject 的 C 库，用于通过 Linux FireWire 字符设备接口执行 IEEE 1394 异步通信。

## 功能概述

- 封装 FireWire 节点、异步请求与响应对象。
- 支持 Function Control Protocol (FCP) 命令与响应。
- 提供 IEEE 1394 周期时间和 OHCI 时间戳解析 API。
- 提供 GLib/GObject 类型、属性、信号和错误域。

## HarmonyOS 适配

- 使用 Meson 和 HarmonyOS clang 构建 AArch64 静态库。
- 使用 OHOS SDK 自带的 Linux FireWire UAPI 头文件。
- 将 GObject Introspection 设为可选；OHOS 构建关闭 GIR 生成，并执行等价的 C API 回归套件。
- 文档生成关闭，不影响库、公开头文件和 pkg-config 元数据。

## 依赖关系

- 编译及运行依赖：`glib2/2.88.0`。
- 构建系统：Meson、Ninja、pkg-config。

## 参考资料

- 官网及发布包：https://www.kernel.org/pub/linux/libs/ieee1394/
- 源码仓库：https://git.kernel.org/pub/scm/libs/ieee1394/libhinawa.git/
