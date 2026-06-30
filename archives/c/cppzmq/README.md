# cppzmq

cppzmq 是 ZeroMQ 的高级 C++ 少绑定（lightweight binding），提供现代 C++ 接口来使用 ZeroMQ 消息库。

## 功能概述

- 提供 `zmq.hpp` 和 `zmq_addon.hpp` 两个头文件
- 封装 ZeroMQ 的 C API 为 C++ 类（context_t, socket_t, message_t 等）
- 支持自动资源管理（RAII）
- header-only 库，无需编译即可使用

## OHOS 适配要点

- header-only 库，无二进制产物（无 .so/.a）
- 依赖 zeromq (libzmq) 4.3.5+
- cmake 配置时需确保 PKG_CONFIG_PATH 包含 libzmq.pc 所在目录
- 使用 `-DCPPZMQ_BUILD_TESTS=OFF` 禁用测试构建（避免 FetchContent 下载 catch2）
- 头文件安装到 `include/` 而非 `include/cppzmq/`（上游默认行为）

## 依赖关系

- **编译依赖**: zeromq (libzmq) ≥ 4.3.5
- **运行依赖**: zeromq (libzmq) ≥ 4.3.5

## 参考资料

- 官网: https://zeromq.org
- 源码: https://github.com/zeromq/cppzmq
- 版本: 4.10.0
