# autobahn-cpp 17.5.1-git7cc5d37 适配笔记

## 源码与构建判断

- 上游来源：`https://github.com/crossbario/autobahn-cpp`，commit
  `7cc5d37bb39bb1c682e1f6c020f62fefa75c0add`。
- 上游是 CMake 工程，顶层只创建 `autobahn_cpp INTERFACE`，并把 examples
  作为可选子目录；本 Conan 配方不构建 examples，直接安装 `autobahn/`
  下全部 `.hpp` 和 `.ipp`，避免把依赖路由器的示例误当作库产物。
- 源码归档 SHA256：
  `b0d2e4d8b2880f0038b1bb303fb46c67b18828fd48fea6091fe6a4df5700895b`。

## 依赖版本

- `boost/1.90.0.4`：Asio 头文件以及下游 CMake 声明的 program_options、
  system、thread、random 组件。
- `openssl/3.5.6`：认证辅助函数和 WebSocket++ TLS 头文件。
- `msgpack-cxx/7.0.0`：WAMP 消息编码。
- `websocketpp/0.8.2.1`：WebSocket++ Asio transport 及其 Boost.Asio 兼容层。

## 源码补丁

`patches/0001-boost-asio-io-context-compat.patch` 修改 Autobahn 自身的
Boost.Asio 和 MessagePack 入口：将三个已不存在的
`boost/asio/io_service.hpp` 包含改为 `io_context.hpp`，在 `boost_config.hpp`
中按 `BOOST_ASIO_VERSION >= 103100` 提供 `boost::asio::io_service = io_context`
别名，并把旧版 MessagePack 的空 array/map 构造改为显式初始化
`msgpack::object`。这样保留 Autobahn 的旧公共 API 和空参数语义，同时使用
当前依赖实现；补丁不绑定 `__OHOS__`。

## 测试设计

上游 commit 没有 `test/` 目录，也没有 CTest/Make test target；只有需要路由器
和额外运行环境的可选 examples。因此 `build()` 不伪造上游测试，
`test_package` 真实编译并运行以下 API：认证 Base64/PBKDF2、WAMP 消息字段、
调用选项的 MessagePack 转换、`io_context` 驱动的会话构造，以及
WebSocket++ transport 模板实例化。测试不发起网络连接。

## 验证记录

本地已完成：源码语言预检（C++，CMake 证据）、源归档 SHA256 校验、依赖配方
可解析性检查、Conan 文件/补丁/测试文件静态检查，以及补丁对干净上游归档的
dry-run。设备端使用该分支最新提交的干净快照运行
`conan create --build=missing`，目标为 OHOS armv8、Clang 15、C++17；依赖均已
解析，autobahn-cpp 成功打包 33 个 `.hpp`、23 个 `.ipp` 和许可证文件，随后
test_package 成功编译并运行 `./test_autobahn_cpp`，输出
`autobahn-cpp consumer test passed`。设备端 CMake 仍报告 `/proc/meminfo`
解析和 jobserver FIFO 权限警告，但不影响本次构建与测试结果。
