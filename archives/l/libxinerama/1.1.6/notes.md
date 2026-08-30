# libXinerama 1.1.6 — HarmonyOS PC 适配笔记

## 上游信息

- 上游版本: libXinerama 1.1.6（2023-08，最新稳定版）
- 上游仓库: https://gitlab.freedesktop.org/xorg/lib/libxinerama
- soname: `-version-number 1:0:0` → `libXinerama.so.1.0.0`

## 依赖分析

`configure.ac`:
```
PKG_CHECK_MODULES(XINERAMA, [x11 >= 1.6] xext xextproto [xineramaproto >= 1.1.99.1])
```

- `x11` / `xext`: 链接级依赖，`libXinerama_la_LIBADD = $(XINERAMA_LIBS)` = -lX11 -lXext
- `xextproto` / `xineramaproto`: 头文件级依赖，xorgproto/2025.1 提供
- 全部在 cmd-pkgs 同轨（libx11/6.4.0 + libxext/6.4.0 + xorgproto/2025.1），无需 vendor

## 适配要点

- 复用 CI 已验证的 OHOS autotools 工具链模式（libxcb/libxi/libxcomposite）
- `generate()`: XINERAMA_CFLAGS（依赖 include 目录）、XINERAMA_LIBS="-lX11 -lXext"
- 头文件级依赖 xorgproto 用 `transitive_headers=True` 消费（知识 E340）
- 导出符号（4 个）: XineramaQueryExtension / XineramaQueryVersion /
  XineramaIsActive / XineramaQueryScreens
- ABI 类型: `XineramaScreenInfo`（12 字节，5 字段固定布局）

## 测试

- `libxinerama_api_surface`: 4 个导出符号强类型重定位
- `libxinerama_version_contract`: XineramaScreenInfo ABI 布局 + Xlib 类型可用性
- 均不依赖 X server
