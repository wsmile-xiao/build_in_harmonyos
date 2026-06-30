# pulseaudio 17.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-25
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. 下载 pulseaudio 17.0 源码 (codeload.github.com)
2. 手动编译安装 libsndfile 1.2.2 依赖 (CMake构建)
3. 创建 .tarball-version 文件（内容 "17.0"，git-version-gen 要求无 v 前缀）
4. 运行 meson setup，禁用 daemon、alsa、dbus 等可选功能，仅构建客户端库
5. 运行 ninja 编译（需要修复 3 个兼容性问题）
6. 运行 meson install --destdir=$TEST_PREFIX 安装到 staging 目录
7. 运行 ohc verify-build 质量门禁验证
8. 运行 ohc package 打包预编译包

```bash
# meson setup 命令
meson setup builddir --prefix=$DEFAULT_PREFIX \
  -Ddaemon=false -Dclient=true \
  -Dalsa=disabled -Dbluez5=disabled -Djack=disabled \
  -Ddbus=disabled -Dudev=disabled -Dsystemd=disabled \
  -Dwebrtc-aec=disabled -Dsamplerate=disabled -Dsoxr=disabled \
  -Dspeex=disabled -Dorc=disabled -Dasyncns=disabled \
  -Dglib=enabled -Dtests=false -Dman=false -Ddoxygen=false

# 环境变量
export PYTHONPATH="/storage/Users/currentUser/usr/local/lib/python3.12/site-packages"
export PATH="/data/service/hnp/bin:$PATH"
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$HOME/usr/local/share/pkgconfig"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接错误 g_libintl_dgettext 未定义 | glib 的 libintl.h 代理头文件将 dgettext 重定义为 g_libintl_dgettext，且 glib_dep.partial_dependency 不链接 glib 库 | 1) 改用完整 glib_dep；2) 禁用 ENABLE_NLS（OHOS 平台不需要 NLS） |
| 2 | gethostid() 在 HarmonyOS 上不可用 | core-util.c 使用 POSIX gethostid()，OHOS/Android 均不支持 | 添加 `__OHOS__` 条件编译守卫，与 `__ANDROID__` 一致返回 NULL |
| 3 | git-version-gen 脚本失败 | 源码来自 tarball，无 git 历史；.tarball-version 需要 "17.0"（无 v 前缀） | 创建 .tarball-version 文件内容为 "17.0" |

## 源码修改

4 个补丁文件:
- 0001-.tarball-version.patch: 新建版本标记文件
- 0002-meson.build.patch: 禁用 ENABLE_NLS（glib libintl.h 代理冲突）
- 0003-src-meson.build.patch: glib_dep.partial_dependency → glib_dep（完整依赖）
- 0004-src-pulsecore-core-util.c.patch: 添加 __OHOS__ gethostid() 守卫

## 依赖版本

| 依赖 | 版本 | 构建系统 |
|------|------|----------|
| libsndfile | 1.2.2 | cmake |
| glib | 2.x (系统预编译) | pkg-config |
| meson | 1.11.0 | python |
| ninja | 1.13.1 | 系统预编译 |

## 验证结果

```bash
ohc verify-build pulseaudio 17.0
# G1-G4 全部通过，质量报告: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pulseaudio-17.0-ohos-aarch64.tar.gz | 7.1M | 预编译包（stripped） |
| pulseaudio-17.0-ohos-aarch64-debug.tar.gz | 3.9M | 调试符号包 |

## 注意事项

- 本次仅构建客户端库（libpulse, libpulse-simple, libpulse-mainloop-glib），不包含 daemon
- NLS（本地化）已禁用，字符串使用英文原文
- 所有外部依赖（glib, libsndfile）已收集到预编译包中
---

**编译结束**: 2026-05-25 22:59
**最终状态**: built
