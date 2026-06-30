# snapcast

Snapcast — 多房间音频同步播放系统，将音频流同步广播到多个播放终端。

- **主页**: https://github.com/badaix/snapcast
- **作者**: Johannes M. (badaix)
- **许可证**: GPLv3+
- **语言**: C++
- **构建系统**: cmake

## 编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.35.0 | built | 2026-05-27 |

## 简介

Snapcast 是一个多房间音频同步播放系统，由 snapserver（服务器端）和 snapclient（客户端端）组成。
服务器端将音频流广播到所有客户端，客户端精确同步播放，延迟控制在毫秒级。

## OHOS 适配

- OpenHarmony musl libc 缺少 pthread_cancel 相关函数，需要 ohos_compat.h/cpp stub 实现
- 使用 CMake -include ohos_compat.h 方式注入兼容层
