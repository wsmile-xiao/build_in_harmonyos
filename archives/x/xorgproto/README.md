# xorgproto - X11 Protocol Headers

## 简介
xorgproto 提供 X Window System 协议的头文件和 pkg-config 配置文件，是编译 X11 相关库的基础依赖。

## 功能
- 提供 X11 核心协议头文件 (X.h, Xproto.h 等)
- 提供 X11 扩展协议头文件 (Xext, Xrender, Xrandr 等)
- 提供 pkg-config 文件用于编译依赖管理

## OHOS 适配
- 使用 meson 构建系统替代 autotools（避免 HMDFS 权限问题）
- 纯头文件包，无需 ELF 签名
- 约 209 个文件（29 个 pkg-config + 151 个头文件）

## 安装
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- xorgproto 2024.1
```

## 使用
```bash
# pkg-config 验证
pkg-config --modversion xproto

# 编译时依赖
pkg-config --cflags xproto
```

## 依赖
- 无外部依赖（纯头文件包）

## 许可证
MIT License

## 更多信息
- 官方网站: https://www.x.org/
- 源码: https://gitlab.freedesktop.org/xorg/proto/xorgproto