# xf86-video-savage 2.4.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
source /storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/.build-context-xf86-video-savage-2.4.1

export PKG_CONFIG_PATH="/storage/Users/currentUser/usr/local/lib/pkgconfig:/storage/Users/currentUser/usr/local/share/pkgconfig:$PKG_CONFIG_PATH"

cd $BUILD_SRC_DIR

./configure --prefix=$DEFAULT_PREFIX \
  --disable-dri --disable-xaa \
  SED=/storage/Users/currentUser/usr/local/bin/sed \
  HELP2MAN=/bin/true \
  MAKEINFO=/bin/true \
  CC=clang CFLAGS="-fPIC -O2" \
  LDFLAGS="-L/storage/Users/currentUser/usr/local/lib" \
  CPPFLAGS="-I/storage/Users/currentUser/usr/local/include"

make -j1
make install DESTDIR=$TEST_PREFIX
make check  # 无测试套件
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess HMDFS 临时目录创建失败 (Permission denied) | HMDFS 上 umask 077 + mktemp 创建的目录不可写 | 在 config.guess 中对 HarmonyOS 跳过 umask 077，直接用 mktemp -d |
| 2 | config.status HMDFS 临时目录问题 | configure 中 umask 077 + mktemp 创建目录不可写 | 在 configure 中对 HarmonyOS 跳过 umask 077（通过 0003-configure.patch 修复，config.status 是生成文件不作为补丁） |
| 3 | savage_xaa.c 编译错误: XAAInfoRec 缺少成员 | OHOS xorg-server 不提供 XAA 支持（XAAInfoRec 结构体为空壳） | configure 使用 --disable-xaa 禁用 XAA 代码编译 |
| 4 | configure 找不到 xorgproto | PKG_CONFIG_PATH 缺少路径 | 扩展 PKG_CONFIG_PATH 包含 share/pkgconfig |

## 源码修改

以下文件被修改（遵循 R2 规则，Phase 3 不生成 .patch）：

### config.guess
- 第 117-127 行: HMDFS 临时目录修复，HarmonyOS 上跳过 umask 077

### configure
- 第 21623-21645 行: HMDFS 临时目录修复，HarmonyOS 上跳过 umask 077

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
# savage_drv.so  savage_drv.la

# make check: 无测试套件（X driver 项目无自测）
```

## 注意事项

- 此驱动在 OHOS 上不支持 DRI (Direct Rendering Infrastructure) 和 XAA 加速架构，仅提供基本帧缓冲支持
- HMDFS 文件系统的 umask 077 + mktemp 问题会影响所有使用此模式的 autotools 项目# make check: 无测试套件（X driver 项目无自测）
```

## 注意事项

- 此驱动在 OHOS 上不支持 DRI (Direct Rendering Infrastructure) 和 XAA 加速架构，仅提供基本帧缓冲支持
- HMDFS 文件系统的 umask 077 + mktemp 问题会影响所有使用此模式的 autotools 项目
---

**编译结束**: 2026-06-08 14:52
**最终状态**: built
