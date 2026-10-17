# libXinerama 1.1.5 — HarmonyOS PC 适配笔记

## 上游信息

- 上游版本: libXinerama 1.1.5（2022-10，对应 soname `libXinerama.so.1.0.0`）
- 上游仓库: https://gitlab.freedesktop.org/xorg/lib/libxinerama
- tarball: https://xorg.freedesktop.org/archive/individual/lib/libXinerama-1.1.5.tar.xz
- 上游 tag 命名为大写 X（libXinerama），conan 包名沿用小写 libxinerama
- soname: `-version-number 1:0:0` → `libXinerama.so.1.0.0`

## 依赖分析

`configure.ac`（与 1.1.6 完全一致）:
```
PKG_CHECK_MODULES(XINERAMA, [x11 >= 1.6] xext xextproto [xineramaproto >= 1.1.99.1])
```

- `x11` / `xext`: 链接级依赖，`libXinerama_la_LIBADD = $(XINERAMA_LIBS)` = -lX11 -lXext
- `xextproto` / `xineramaproto`: 头文件级依赖，xorgproto/2025.1 提供
- W0 download 实测（2026-09-11）：libx11/6.4.0、libxext/6.4.0、xorgproto/2025.1 均已在制品仓发布（conan download --only-recipe 全部通过）

## 适配要点

- 配方与仓内已合入的 libxinerama/1.1.6 同构（上游 1.1.5→1.1.6 源码仅 329 行单文件 src/Xinerama.c，API 面完全一致）
- 复用 CI 已验证的 OHOS autotools 工具链模式（libxcb/libxi/libxcomposite/libxinerama 1.1.6）
- `generate()`: XINERAMA_CFLAGS（依赖 include 目录）、XINERAMA_LIBS="-lX11 -lXext"
- 头文件级依赖 xorgproto 用 `transitive_headers=True` 消费（知识 E340）
- 导出符号（4 个）: XineramaQueryExtension / XineramaQueryVersion /
  XineramaIsActive / XineramaQueryScreens（与 1.1.6 一致）
- ABI 类型: `XineramaScreenInfo`（12 字节，5 字段固定布局，与 1.1.6 一致）

## 上游测试核验（N=注册数实测）

- 解包 libXinerama-1.1.5.tar.xz 实测：无 `test/` 目录，根 Makefile.am 与 src/Makefile.am 均无 `check_PROGRAMS`/`TESTS` 注册
- `make check` 目标存在但零注册用例（X11 轻量客户端库惯例）
- 上游注册测试数 N=0

## 测试

- `libxinerama_api_surface`: 4 个导出符号强类型重定位
- `libxinerama_version_contract`: XineramaScreenInfo ABI 布局 + Xlib 类型可用性
- 均不依赖 X server
