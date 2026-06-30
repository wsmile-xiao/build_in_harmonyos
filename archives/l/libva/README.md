# libva

libva (Video Acceleration API) 是一个视频加速API库，提供视频解码和编码的硬件加速支持，主要用于Intel GPU。

## OHOS 适配

### 已知问题
- **X11依赖缺失**: 缺少完整的X11依赖栈（libxfixes, xcb, xcb-dri3等），无法启用GLX支持
- **meson编译器识别**: meson构建系统需要显式设置CC/CXX/AR环境变量（完整路径）
- **libdrm软链接**: 预编译包缺少.so软链接，需手动创建

### 当前状态
- 编译状态: partial（仅编译基础版本：libva + libva-drm）
- 未启用: GLX支持（需要完整X11依赖栈）

## 依赖

### 运行时依赖
- libdrm 2.4.133

### 未满足依赖（GLX需要）
- libxfixes
- xcb
- xcb-dri3

## 功能验证

```bash
pkg-config --modversion libva
# 1.23.0

ls ~/usr/local/lib/libva*.so*
# libva.so.2.2300.0
# libva-drm.so.2.2300.0
```

## 参考

- 官网: https://github.com/intel/libva
- 源码: https://github.com/intel/libva/releases/download/2.23.0/libva-2.23.0.tar.gz
