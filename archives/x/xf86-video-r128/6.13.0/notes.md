# xf86-video-r128 6.13.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
source /storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/.build-context-xf86-video-r128-6.13.0

export PKG_CONFIG_PATH="/storage/Users/currentUser/usr/local/lib/pkgconfig:/storage/Users/currentUser/usr/local/share/pkgconfig:$PKG_CONFIG_PATH"

cd $BUILD_SRC_DIR

./configure --prefix=$DEFAULT_PREFIX \
  --disable-dri --disable-exa \
  SED=/storage/Users/currentUser/usr/local/bin/sed \
  HELP2MAN=/bin/true \
  MAKEINFO=/bin/true \
  CC=clang CFLAGS="-fPIC -O2" \
  LDFLAGS="-L/storage/Users/currentUser/usr/local/lib" \
  CPPFLAGS="-I/storage/Users/currentUser/usr/local/include"

make -j1
make install DESTDIR=$TEST_PREFIX
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 "cannot guess build type" | config.guess/config.sub 不识别 HarmonyOS 平台 | 修改 config.guess: UNAME_SYSTEM 添加 HarmonyOS case；aarch64 machine 添加 aarch64:HarmonyOS 映射。修改 config.sub: 添加 harmonyos* → kernel=linux,os=musl |
| 2 | configure 创建临时目录失败 (Permission denied) | HMDFS 上 umask 077 + mktemp 创建的目录不可写 | 在 config.guess 和 configure 中对 HarmonyOS 跳过 umask 077，直接用 mktemp -d |
| 3 | r128_driver.c 编译错误: BIOSseg/xf86int10Addr 未定义 | OHOS xf86int10.h 是 stub，不定义 BIOSseg 和 xf86int10Addr | 用 #ifdef __OHOS__ 守卫跳过 Int10 BIOS 读取代码块，让驱动 fall through 到 PCI ROM 路径 |
| 4 | r128_crtc.c/r128_exa_render.c 大量 DRI/EXA 错误 | OHOS xorg-server 不提供 DRI/EXA 支持 | configure 使用 --disable-dri --disable-exa 禁用 DRI/EXA 代码编译 |
| 5 | configure 找不到 xorgproto 依赖 | PKG_CONFIG_PATH 缺少 /storage/Users/currentUser/usr/local/share/pkgconfig | 安装 xorgproto 2024.1 预编译包并扩展 PKG_CONFIG_PATH |

## 源码修改

以下文件被修改并保存为 patch 文件：

### config.guess (0001-config.guess.patch)
- HMDFS 临时目录修复，HarmonyOS 上跳过 umask 077
- UNAME_SYSTEM 检测添加 HarmonyOS/OpenHarmony case
- aarch64:HarmonyOS 和 aarch64_be:HarmonyOS machine pattern 映射

### config.sub (0002-config.sub.patch)
- 添加 harmonyos* case pattern → kernel=linux, os=musl

### configure (0003-configure.patch)
- HMDFS 临时目录创建修复，HarmonyOS 上跳过 umask 077

### src/r128_driver.c (0004-src-r128_driver.c.patch)
- 用 #ifdef __OHOS__ 守卫跳过 pInt10->BIOSseg 和 xf86int10Addr() 调用

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| xorgproto | 2024.1 | 预编译包 (cmd-pkgs) |
| xorg-server | 21.1.15 | 预编译包 |
| pixman | 0.42.2 | 预编译包 |
| libpciaccess | 0.18 | 预编译包 |

## 验证结果

```bash
# 编译产物
ls $TEST_PREFIX/$DEFAULT_PREFIX/lib/xorg/modules/drivers/
# r128_drv.so  r128_drv.la

# 编译警告（非致命）
# r128_crtc.c: unused variables, void pointer arithmetic (GNU extension)
# r128_cursor.c: void pointer arithmetic (GNU extension)
# r128_output.c: format string not literal

# make check: 无测试套件（X driver 项目无自测）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| r128_drv.so | 84352 bytes | ATI Rage 128 Xorg 驱动模块 |
| r128_drv.la | 994 bytes | libtool 链接描述文件 |
| r128.4 | man page | 驱动手册页 |

## 注意事项

- 此驱动在 OHOS 上不支持 DRI (Direct Rendering Infrastructure) 和 EXA 加速架构，仅提供基本帧缓冲支持
- Int10 BIOS 读取功能在 OHOS 上不可用（xf86int10.h 为 stub），驱动将使用 PCI ROM 路径读取 VBIOS
- HMDFS 文件系统的 umask 077 + mktemp 问题会影响所有使用此模式的 autotools 项目
---

**编译结束**: 2026-06-08 13:48
**最终状态**: built
