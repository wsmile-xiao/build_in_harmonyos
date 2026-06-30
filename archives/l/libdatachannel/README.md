# libdatachannel

C/C++ WebRTC 网络库，支持 Data Channels、Media Transport 和 WebSocket。基于 libjuice（ICE）和 usrsctp（SCTP）实现 WebRTC 标准。

## 功能概述

- WebRTC Data Channels（可靠/不可靠传输）
- WebSocket 支持
- Media Transport（音频/视频流）
- 跨平台 C/C++ API
- 内嵌子模块：libjuice、usrsctp、libsrtp、nlohmann-json、plog

## OHOS 适配要点

- **BSD 类型缺失**：OHOS 缺少 `u_int/u_long/u_char/caddr_t` 等 BSD 类型，需通过 `-include ohos_compat.h` 注入兼容头
- **usrsctp 需填充**：内嵌 usrsctp 的 `user_socketvar.h` 原为空文件，补丁填充了 BSD socket 结构定义
- **libsrtp 版本**：必须是 v2.x 系列（v3.0.0 的 target 名 `srtp3` 与 libdatachannel 不兼容）
- **OpenSSL 路径**：需通过 cmake 显式指定 OpenSSL 头文件和库路径（pkg-config 可能指向错误版本）
- **cmake C flags**：`CMAKE_C_FLAGS=-include ohos_compat.h` 是必需的编译选项，仅在 C 编译中生效（C++ 代码不使用 BSD 类型）

## 依赖关系

- 编译依赖：OpenSSL 1.1.1w
- 内嵌子模块（无需外部安装）：libjuice、usrsctp、libsrtp 2.5.0、nlohmann-json、plog

## 参考资料

- 官网：https://libdatachannel.org
- 源码仓库：https://github.com/paullouisageneau/libdatachannel