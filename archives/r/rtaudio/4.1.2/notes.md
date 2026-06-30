# rtaudio 4.1.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 运行 `libtoolize --copy --install` 和 `autoreconf --verbose --install --force` 生成 configure 脚本
2. 运行 `./configure --prefix=/storage/Users/currentUser/usr/local` — ALSA 音频 API 被自动检测并启用
3. 修改 RtAudio.cpp：为 `pthread_testcancel` 添加 `#ifdef __OHOS__` 兼容定义
4. `make -j2` 编译成功
5. `make install DESTDIR=$TEST_PREFIX` — staging 安装
6. `make install` — 安装到 DEFAULT_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `pthread_testcancel` undeclared | OpenHarmony musl libc 不提供 pthread_testcancel | 在 RtAudio.cpp 中 `#ifdef __OHOS__` 守卫下定义 `#define pthread_testcancel() ((void)0)` |
| 2 | autoreconf 失败 (LIBTOOL undefined) | 缺少 libtool m4 文件 | 先运行 `libtoolize --copy --install`，创建 m4 目录 |

## 源码修改

- RtAudio.cpp: 在 `#include` 后添加 `#ifdef __OHOS__` 守卫的 pthread_testcancel 空宏定义

## 依赖版本

- alsa-lib 1.2.12（预编译包）
- pthread（系统提供）

## 验证结果

```bash
make check — 无自动化测试套件（音频库需要硬件）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| librtaudio.so.5.0.0 | ~369KB | 共享库 |
| librtaudio.a | ~369KB | 静态库 |
| RtAudio.h | ~47KB | 头文件 |
| rtaudio.pc | — | pkg-config 文件 |

## 注意事项

- rtaudio 默认使用 ALSA 音频 API，需要 alsa-lib 预编译包
- pthread_testcancel 在 musl libc 中不可用，需要平台适配补丁
---

**编译结束**: 2026-05-29 10:52
**最终状态**: built
