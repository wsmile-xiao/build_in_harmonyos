# libXext

## 简介
libXext 是 X11 的杂项扩展库，提供 SHAPE、SHM、SYNC、DBE 等扩展功能。

## OHOS 适配
- **构建系统**: autotools configure 在 HarmonyOS 上受限，采用手动编译
- **依赖链**: 需要 xorgproto → xcb-proto → libXau → libxcb → xtrans → libX11（8层依赖）
- **编译选项**: 必须使用 `-fPIC` 确保位置无关代码

## 依赖
- libX11 1.8.7
- libxcb 1.16
- xorgproto 2024.1

## 功能验证
```bash
pkg-config --modversion xext  # 期望输出: 1.7.0
```

## 参考
- 官网: https://www.x.org/
- 源码: https://gitlab.freedesktop.org/xorg/lib/libxext
