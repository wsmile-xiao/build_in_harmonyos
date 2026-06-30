# snapcast 0.35.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-27
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

1. `python3 $SKILL_ROOT/scripts/ohc-run.py init-build snapcast 0.35.0 --url=https://github.com/badaix/snapcast/archive/refs/tags/v0.35.0.tar.gz`
2. cmake 配置（需要设置 PKG_CONFIG_PATH）
3. make -j2 → make install DESTDIR=$TEST_PREFIX → make install（不带 DESTDIR）
4. `python3 $SKILL_ROOT/scripts/ohc-run.py package snapcast 0.35.0`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pthread_setcancelstate undeclared | OpenHarmony musl libc 缺少 pthread 取消函数 | 创建 ohos_compat.h(声明)+ohos_compat.cpp(stub), CMake -include 强制注入 |
| 2 | Avahi 不可用 | 无 Avahi 预编译包 | BUILD_WITH_AVAHI=OFF |
| 3 | CMAKE_SYSTEM_NAME 为 "HarmonyOS" | 平台检测 | 使用 MATCHES "HarmonyOS" 条件判断 |

## 源码修改

- CMakeLists.txt: 添加 __OHOS__ 定义和 -include ohos_compat.h
- common/CMakeLists.txt: 添加 ohos_compat.cpp 到 HarmonyOS 构建
- common/ohos_compat.cpp: 新增 pthread_setcancelstate stub 实现
- common/ohos_compat.h: 新增 pthread_setcancelstate stub 声明

补丁: 0001-CMakeLists.txt.patch, 0002-common-CMakeLists.txt.patch, 0003-common-ohos_compat.cpp.patch, 0004-common-ohos_compat.h.patch

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| alsa-lib | 1.2.12 | 预编译 |
| Boost | 1.84.0 | 预编译(header-only) |
| FLAC | 1.4.3 | 预编译 |
| libogg | 1.3.5 | 预编译 |
| libvorbis | 1.3.7 | 预编译(静态) |
| libopus | 1.4 | 预编译 |
| soxr | 0.1.3 | 预编译 |
| OpenSSL | 1.1.1w | 预编译 |
| expat | 2.7.1 | 预编译 |

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/snapserver --version
snapserver v0.35.0

$ /storage/Users/currentUser/usr/local/bin/snapclient --version
snapclient v0.35.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| snapcast-0.35.0-ohos-aarch64.tar.gz | 18882KB | 预编译包 |
| snapcast-0.35.0-ohos-aarch64-debug.tar.gz | - | 调试符号包 |

## 注意事项

- Avahi 已禁用，mDNS 发现功能不可用
- libvorbis 仅有静态库(.a)，需要 BUILD_SHARED_LIBS=OFF
- PKG_CONFIG_PATH 必须包含 /storage/Users/currentUser/usr/local/lib/pkgconfig
---

**编译结束**: 2026-05-27 15:19
**最终状态**: built
