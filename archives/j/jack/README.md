# jack

JACK Audio Connection Kit — 低延迟音频服务器和连接框架，用于专业音频应用之间的实时音频路由。

- **主页**: https://jackaudio.org
- **许可证**: GPLv2+ (jack2), LGPLv2.1+ (libjack)
- **语言**: C/C++
- **构建系统**: waf (custom Python-based)

## 编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.9.22 | built | 2026-05-27 |

## 简介

JACK (JACK Audio Connection Kit) 是专业级低延迟音频服务器，允许多个音频应用之间实时路由音频数据。
jack2 是 JACK 的 C++ 实现，支持多处理器并行处理。

## OHOS 适配

- OpenHarmony musl libc 不支持 pthread_cancel/pthread_setcanceltype，需 #ifndef __OHOS__ 守卫
- waf 构建系统的 waflib/Context.py 使用 imp.new_module，Python 3.12+ 已移除 imp 模块
- ALSA 驱动 hammerfall.c 中的 pthread_cancel 调用需 __OHOS__ 守卫
- JackPosixThread.h 的 PTHREAD_CANCEL_ASYNCHRONOUS 在 OpenHarmony 未定义
- DBus 支持需禁用（OpenHarmony 无 DBus）
- libsamplerate 非硬依赖，可安全禁用
