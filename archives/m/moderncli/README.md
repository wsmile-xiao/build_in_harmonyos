# moderncli

moderncli 是一个 C++17 header-only 库，提供跨平台的网络、socket、SSL、线程、加密和串行 I/O 支持。

## 描述
moderncli 设计为简洁高效的现代 C++ 库，无需编译二进制，只需包含头文件即可使用。

## 功能
- 网络和 Socket 操作
- SSL/TLS 加密通信
- 线程和进程管理
- 加密和签名功能
- 串行 I/O 支持
- 文件系统操作

## OHOS 适配要点
- Header-only 库，直接安装头文件
- 需要 fmt 库作为依赖
- OHOS SDK C++ 标准库与 C++17 nullptr_t 有兼容性问题（已记录）

## 依赖
- openssl
- fmt (12.1.0)

## 安装
头文件安装在 `~/usr/local/include/moderncli/`

## 参考资料
- GitLab: https://gitlab.com/tychosoft/moderncli