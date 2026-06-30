# MangoHud

MangoHud 是一个 Vulkan/OpenGL overlay 层，用于监控 FPS、温度、CPU/GPU 负载等信息。

## 描述
MangoHud 是一个开源的 Vulkan 和 OpenGL overlay 层，可以显示帧率、CPU/GPU 使用率、温度等信息。它兼容大多数 Vulkan 和 OpenGL 应用程序。

## 已编译版本
- 0.8.4 (2026-06-04)

## 依赖
- Vulkan Loader 1.3.295
- libX11 6.4.0
- libdrm 2.4.133
- dbus 1.14.10

## 特性
- Vulkan overlay 支持
- OpenGL overlay 支持（libMangoHud_opengl.so）
- FPS、温度、CPU/GPU 负载监控
- 自定义配置和预设

## 使用方法
```bash
# 启动带 MangoHud overlay 的程序
mangohud ./your_application

# 配置
vim ~/.config/MangoHud/MangoHud.conf
```

## 注意事项
- 需要 Vulkan Loader 支持
- Wayland 模式已禁用（当前平台不支持）