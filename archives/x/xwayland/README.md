# Xwayland

## 软件介绍
Xwayland 是 X.Org Server 的一个 DDX (Device Dependent X) 驱动，用于在 Wayland compositor 下运行传统 X11 应用程序。它作为 X server 和 Wayland client 的桥接，让 X11 应用程序可以在 Wayland 环境中无缝运行。

## 核心特性
- 兼容传统 X11 应用程序
- 与 Wayland compositor 集成
- 支持输入设备（键盘、鼠标、触摸）
- 支持多显示器配置

## 版本说明
- 版本 24.1 基于 xorg-server xwayland-24.1 分支
- 使用 Meson 构建系统
- 禁用了非核心功能（GLX、DRI、systemd、udev）

## OHOS 适配要点
1. **构建系统**: Meson，需要配置禁用多项桌面依赖
2. **依赖**: wayland、wayland-protocols >= 1.38、pixman、libdrm、nettle 等
3. **RPATH**: 需要手动设置 `$ORIGIN/../lib` 相对路径
4. **签名**: ELF 文件必须签名才能在鸿蒙上执行
5. **无 systemd**: 不依赖 systemd，适合嵌入式环境

## 依赖关系
- wayland (>= 1.23.1)
- wayland-protocols (>= 1.38)
- libXfont2
- xkbcomp
- libxshmfence
- libxcvt
- pixman
- libdrm
- nettle (用于 SHA1)

## 使用方法
Xwayland 通常不直接运行，而是由 Wayland compositor（如 weston、mutter）自动启动。用户无需手动干预。

如果需要手动测试：
```bash
# 设置库路径
export LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib:$LD_LIBRARY_PATH

# Xwayland 需要连接到 Wayland compositor
Xwayland :1
```

## 限制说明
- 本版本禁用了 GLX/DRI，不支持 OpenGL 渲染
- 无 systemd 集成
- 需要 Wayland compositor 配合运行

## 相关链接
- 官网: https://www.x.org/
- 源码: https://gitlab.freedesktop.org/xorg/xserver/
- 文档: https://wayland.freedesktop.org/xwayland.html