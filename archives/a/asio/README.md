# ASIO

ASIO 是一个跨平台的 C++ 网络和底层 I/O 编程库，提供异步 I/O 模型，支持 TCP/UDP 网络编程、串口通信、信号处理等功能。

## 功能概述

- **异步 I/O 模型**：基于 Proactor 模式的高性能异步 I/O
- **网络编程**：TCP/UDP socket、acceptor、resolver
- **定时器**：deadline_timer、steady_timer
- **串口通信**：serial_port 支持
- **信号处理**：signal_set 信号集
- **SSL/TLS 支持**：需要 OpenSSL（可选）
- **协程支持**：C++20 协程和 stackful 协程

## OHOS 适配

### 特性
- **Header-only 库**：无需编译二进制，只需安装头文件
- **无依赖**：核心功能不依赖外部库
- **可选依赖**：OpenSSL 提供 SSL/TLS 支持

### 已知问题
- autotools 构建系统在 HarmonyOS 环境下存在兼容性问题
- 建议使用自定义安装脚本直接复制头文件

### 与 Linux 的差异
- 安装方式：直接复制头文件到 `/usr/local/include` 或 `$HOME/usr/local/include`
- 使用时需指定头文件路径：`-I/path/to/include`

## 依赖关系

### 编译依赖
- 无必需依赖（header-only 库）

### 可选依赖
- **OpenSSL**: 提供 SSL/TLS 支持
  - 编译时需链接 `-lssl -lcrypto`
  - 使用时定义 `ASIO_USE_SSL`

## 使用方式

```bash
# 安装头文件（已编译版本）
# 预编译包会安装到 $HOME/usr/local/include/

# 编译时包含头文件
g++ -I$HOME/usr/local/include my_app.cpp -o my_app

# 使用 SSL 支持
g++ -I$HOME/usr/local/include -DASIO_USE_SSL my_app.cpp -o my_app -lssl -lcrypto

# CMake 集成
# CMakeLists.txt:
# include_directories($ENV{HOME}/usr/local/include)
```

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [1.30.2](./1.30.2/) | built | 2026-05-22 |

## 参考资料

- 官网: https://think-async.com/Asio/
- GitHub: https://github.com/chriskohlhoff/asio
- 文档: https://think-async.com/Asio/asio-1.30.2/doc/