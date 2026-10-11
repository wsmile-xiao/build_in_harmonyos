# libhinawa 4.0.2 HarmonyOS PC 适配记录

## 源码与依赖

- 官方发布包：`https://www.kernel.org/pub/linux/libs/ieee1394/libhinawa-4.0.2.tar.xz`
- SHA256：`48816e94a74528f5d4f13e1b6ffe74eb79cba6e46842181a5405aad5bc1263d7`
- 构建系统：Meson 0.60 以上
- Conan 依赖：`glib2/2.88.0`，已用 `conan download --only-recipe` 验证制品仓可用。

## 上游测试基线

上游 `tests/meson.build` 注册 7 项 Python/GObject Introspection 测试：
`fw-node`、`fw-req`、`fw-resp`、`fw-fcp`、`cycle-time`、
`hinawa-enum`、`hinawa-functions`。在未修改的 4.0.2 源码上执行
`meson test`，实测 7/7 通过。这些用例仅检查公开对象、属性、信号、枚举、
错误域和时间戳 API，不打开 FireWire 设备。

HarmonyOS 环境没有可用的 `g-ir-scanner`/PyGObject 目标侧链路。因此补丁仅在
关闭 `introspection` 时，以 7 项 C API 测试逐项覆盖同一组公开接口；启用
`introspection` 时仍原样运行上游 Python 测试。配方构建阶段执行 `meson.test()`，
任何一项失败都会使构建失败。

## HarmonyOS 适配

1. 新增 Meson `introspection` 布尔选项，默认开启，保持上游默认行为。
2. OHOS 配方关闭 GIR/typelib 生成，避免依赖不可执行的扫描工具。
3. 使用 SDK 的 `<linux/firewire-cdev.h>` 和 `<linux/firewire-constants.h>`；无需修改库源码。
4. 默认构建静态库，由 Conan 显式传播 GLib/GObject 依赖。

## 测试结果

- 未修改上游源码原生测试：7/7 通过。
- OHOS 构建阶段等价回归测试：7/7 通过。
- Conan 消费者测试：8/8 通过，其中第 8 项为 HarmonyOS PC AArch64 ABI、字节序和 OHCI 时间戳解析专项测试。
