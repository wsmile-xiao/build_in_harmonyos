# libxkbfile 1.1.3 适配笔记

## 概述

XKB keymap 文件格式（.xkm / XKB keymap 源码）客户端库，提供 XKB 文件
读写、格式转换、TOC 解析与 keymap 语义输出 API。libxkbfile.so.1。

## OHOS 适配要点

- **依赖**：libx11/6.4.0、xorgproto/2025.1（cmd-pkgs track）。configure
  运行 `PKG_CHECK_MODULES(XKBFILE, x11 kbproto)`；kbproto 由 xorgproto
  提供（纯头文件），libxkbfile 只链接 `-lX11`。
- **构建系统**：autotools，复用 libxcb/libxi 的 OHOS 工具链模式
  （clang、CONFIG_SHELL、TMPDIR 进 build 目录、-j1、.pc 相对化）。
- **版本**：`-version-number 1:0:2` → libxkbfile.so.1.0.2（meson 亦为
  1.0.2）。注意 libxkbfile 是全小写文件名（`libxkbfile.so`），不遵循
  X 库 `libX<Name>` 惯例，Conan `cpp_info.libs` 必须用小写 `xkbfile`。
- **配置选项**：`--disable-docs --disable-specs --without-xmlto
  --without-fop --without-xsltproc`（文档工具不可用，跳过 man 生成）。
- **pkg-config**：xkbfile.pc 的 `Name: xkbfile`；`Requires: kbproto`、
  `Requires.private: x11`。Conan pkg_config_name 设为 `xkbfile`。
- **works-check 陷阱（关键）**：本机模式（`--build == --host`）下 autoconf
  会尝试*执行* conftest 二进制，被 OHOS 沙箱拦截（`C compiler cannot create
  executables`，worker 相关、非确定）。`generate()` 里 `update_configure_args`
  强制 `--build=aarch64-unknown-linux-ohos --host=aarch64-linux-ohos`，
  raw triplet 不同 → 进入交叉模式，works-check 仅链接不运行即通过。
- **config.guess/config.sub 补丁（必须）**：本包 config.guess 2023-01-01 /
  config.sub 2023-01-21，与 libxpm 3.5.17 完全一致——直接复用 libxpm 的两个
  conandata 补丁（`0001-config.sub.patch` 加 `ohos*` 合法 OS +
  `linux-ohos*` kernel-os；`0002-config.guess.patch` 在 NetBSD 分支前插入
  HarmonyOS 分支直接 `echo aarch64-unknown-linux-ohos; exit`，避免 fall
  through 编译 dummy.c 被沙箱拦截）。`build()` 在 configure 前
  `apply_conandata_patches`。

## 测试

test_package 构建两个无需 X server 的可执行文件：

1. `libxkbfile_api_surface` — 对 libxkbfile.so.1 全部 54 个导出函数
   生成强制活重定位（Xkb*/Xkm*，排除宏与内部符号）。
2. `libxkbfile_version_contract` — 校验 XkbFileInfo ABI 布局
   （type/defined 两个 unsigned + 末尾 XkbDescPtr 指针，64 位下 16 字节）、
   XkbXKMFile..XkbMessage 常量，
   以及 XkbKeysymText/XkbKeyNameText/XkbAtomText 的签名契约。

## 参考

- 官网: https://gitlab.freedesktop.org/xorg/lib/libxkbfile
- 源码: https://xorg.freedesktop.org/archive/individual/lib/libxkbfile-1.1.3.tar.xz
