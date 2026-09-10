# libpciaccess

## 简介

libpciaccess 是 X.Org 提供的通用 PCI 总线访问库，为图形栈和系统组件提供 PCI 设备枚举、配置空间访问及设备属性查询 API。

## OHOS 适配

- 构建系统：Meson
- HarmonyOS 使用 Linux sysfs 后端
- Meson 平台检测需同时接受 `linux` 与 `harmonyos`
- Conan 包默认构建静态库，避免与系统同名库冲突

## 依赖

- zlib 1.3.1

## 功能验证

消费者测试初始化 PCI 子系统、创建迭代器、遍历设备、调用 0.19 新增的 `pci_device_is_boot_display()`，并清理资源；沙箱无 PCI sysfs 权限时验证标准错误契约。

## 参考

- https://gitlab.freedesktop.org/xorg/lib/libpciaccess
- https://www.x.org/releases/individual/lib/libpciaccess-0.19.tar.xz
