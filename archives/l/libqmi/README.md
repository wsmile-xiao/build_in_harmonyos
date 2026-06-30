# libqmi

## 简介

libqmi 是 QMI（Qualcomm MSM Interface）协议的 GLib 实现，用于与 Qualcomm 调制解调器通信。

## OHOS 适配

### 关键问题

1. **sockaddr_storage 重定义冲突**：与 libqrtr-glib 相同的问题，需要特殊处理。

2. **libintl 符号缺失**：glib 的 g_libintl_* 函数需要链接 libintl.a 静态库。

3. **禁用功能**：
   - udev（鸿蒙无 udev）
   - introspection（缺少 gobject-introspection）
   - man（文档生成）

### 与 Linux 的差异

- Linux：完整 udev/introspection 支持
- OHOS：需要禁用部分功能

## 依赖

- glib-2.0 >= 2.0

## 功能验证

```bash
qmicli --version
pkg-config --modversion qmi-glib
```

## 参考

- 官网：https://www.freedesktop.org/wiki/Software/libqmi/