# uSockets

**描述**: Cross-platform asynchronous networking library for C.

高效跨平台异步网络 C 库，是 uWebSockets 的底层网络引擎。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.7.1 | built (功能验证通过) | 通过 uWebSockets 间接验证 |

## 版本索引

| 版本 | 日期 | 状态 |
|------|------|------|
| 0.7.1 | 2026-06-24 | built (功能验证通过) |

## 依赖

- OpenSSL >= 3.0
- zlib >= 1.2

## 鸿蒙适配状态

- ✅ 编译成功 (静态库 uSockets.a, WITH_OPENSSL=1)
- ✅ 功能测试通过 (通过 uWebSockets 上层验证)
- ✅ 头文件 libusockets.h 安装到 ~/usr/local/include/
