# wayland-protocols

## 简介
Wayland 协议扩展定义集合，包含稳定版、实验版和未稳定版的 Wayland 协议 XML 定义文件。

## 编译版本
- 1.27 (2026-06-02)

## 项目信息
- 官方网站: https://wayland.freedesktop.org/
- 源码仓库: https://gitlab.freedesktop.org/wayland/wayland-protocols
- 许可证: MIT/Expat

## 构建系统
- Meson >= 0.55.0

## 依赖
- 无编译依赖（纯协议文件）
- 测试依赖: wayland-scanner（可选，通过 -Dtests=false 禁用）

## 安装位置
- 协议文件: ~/usr/local/share/wayland-protocols/
- pkg-config 文件: ~/usr/local/share/pkgconfig/wayland-protocols.pc

## 编译选项
```bash
meson setup builddir --prefix=$DEFAULT_PREFIX -Dtests=false
ninja -C builddir
ninja -C builddir install
```

## 注意事项
- wayland-protocols 是协议定义文件包，不包含可执行代码
- 测试需要 wayland-scanner，但可通过 -Dtests=false 禁用测试
- 编译产物为 XML 协议文件和 pkg-config 元数据
