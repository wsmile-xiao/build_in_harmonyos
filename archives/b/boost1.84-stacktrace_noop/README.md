# boost1.84-stacktrace_noop

Boost.Stacktrace noop 是 Boost 官方提供的“禁用堆栈回溯”后端。它保留
Boost.Stacktrace 的公开 API，但捕获结果始终为空，适合不具备或不允许使用
栈展开、动态符号解析及外部符号化工具的构建。

## 功能概述

- 提供完整的 Boost 头文件树。
- 提供静态库 `libboost_stacktrace_noop.a`。
- 提供独立 CMake 目标
  `boost1.84-stacktrace_noop::stacktrace_noop`。
- 保持 `boost::stacktrace::stacktrace`、格式化和安全 dump API 可用，同时
  不收集实际调用帧。

## HarmonyOS 适配

- Boost.Build 在当前 HarmonyOS 环境存在 E068 兼容问题，配方直接编译
  官方 `libs/stacktrace/src/noop.cpp`。
- 只构建静态库，避免与系统库发生动态链接冲突。
- 通过 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 特性宏保护 HarmonyOS musl
  未提供的 pthread cancellation API。
- noop 后端不依赖 libbacktrace、`dladdr`、addr2line、WinDbg 或 ptrace。

## 依赖关系

本包没有第三方 Conan 编译依赖或运行依赖。C++ 运行时由 HarmonyOS SDK
工具链提供。

## CMake 消费示例

```cmake
find_package(boost1.84-stacktrace_noop REQUIRED CONFIG COMPONENTS stacktrace_noop)
target_link_libraries(app PRIVATE boost1.84-stacktrace_noop::stacktrace_noop)
```

## 交叉编译测试

配方默认直接执行测试程序，供原生 HarmonyOS 构建机使用。在 Windows 等
交叉编译主机上，可显式设置 `BOOST_STACKTRACE_NOOP_HDC` 为 DevEco SDK 的
`hdc` 路径；此时 6 个上游测试和 `test_package` 消费者测试会被发送到
HarmonyOS 设备运行，并严格检查设备端退出码。

可选设置 `BOOST_STACKTRACE_NOOP_HDC_TARGET` 选择 HDC 设备，设置
`BOOST_STACKTRACE_NOOP_HDC_REMOTE_DIR` 修改设备端临时目录。未设置 HDC
变量时，原有的原生 Conan/CI 行为不变。

## 参考资料

- [Boost.Stacktrace 1.84.0 文档](https://www.boost.org/doc/libs/1_84_0/libs/stacktrace/)
- [Boost 1.84.0 官方源码](https://archives.boost.io/release/1.84.0/source/)
- [Boost 软件许可证](https://www.boost.org/LICENSE_1_0.txt)
