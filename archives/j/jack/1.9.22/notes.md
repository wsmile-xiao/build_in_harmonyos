# jack 1.9.22 适配笔记

## 编译环境
- 构建系统: waf (custom Python-based)
- 编译日期: 2026-05-27
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. `python3 $SKILL_ROOT/scripts/ohc-run.py init-build jack 1.9.22 --url=https://github.com/jackaudio/jack2/archive/refs/tags/v1.9.22.tar.gz`
2. 源码修改：添加 `#ifndef __OHOS__` 守卫到 pthread_cancel 相关调用（4处修改）
3. 修改 waflib/Context.py：替换 `imp.new_module` 为 `types.ModuleType`（Python 3.12+兼容）
4. 运行 `./waf configure --prefix=$DEFAULT_PREFIX --samplerate=no --dbus=no`
5. 运行 `./waf build`
6. 运行 `./waf install --destdir=$TEST_PREFIX`（staging）
7. 运行 `./waf install`（本地安装）
8. `ohc-run.py package jack 1.9.22`
9. `ohc-run.py finish jack 1.9.22 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pthread_cancel undeclared | OpenHarmony musl libc 缺少 pthread 取消函数 | #ifndef __OHOS__ 条件编译守卫 |
| 2 | imp.new_module 不存在 | Python 3.12+ 已移除 imp 模块 | 替换为 types.ModuleType |
| 3 | PTHREAD_CANCEL_ASYNCHRONOUS 未定义 | OHOS 无此常量 | JackPosixThread.h 添加 __OHOS__ 守卫 |
| 4 | ALSA hammerfall.c pthread_cancel | 同问题1 | 同方案1 |
| 5 | DBus 检测失败 | OpenHarmony 无 DBus | --dbus=no 禁用 |

## 源码修改

- 0001-common-JackControlAPI.cpp.patch: pthread_cancel/pthread_setcanceltype 守卫
- 0002-linux-alsa-hammerfall.c.patch: ALSA驱动 pthread_cancel 守卫
- 0003-posix-JackPosixThread.h.patch: PTHREAD_CANCEL_ASYNCHRONOUS 守卫
- 0004-waflib-Context.py.patch: imp.new_module → types.ModuleType

## 依赖版本
- libpthread (system, musl libc)
- libasound (system ALSA)
- libsamplerate: 禁用

## 验证结果
- jackd --version 可执行
- 预编译包已制作并签名

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| jack-1.9.22-ohos-aarch64.tar.gz | 6.2M | 预编译包 |
| jack-1.9.22-ohos-aarch64-debug.tar.gz | 2.0M | debug包 |

---

**编译结束**: 2026-05-27 15:17
**最终状态**: built