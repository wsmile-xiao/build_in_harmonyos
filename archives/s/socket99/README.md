# socket99

socket99 是一个为 BSD sockets API 提供更简洁 C99 配置接口的静态 C 库。

## 功能概述

- TCP/UDP 客户端和服务端
- Unix domain stream/datagram socket
- 阻塞与非阻塞 socket
- IPv4、IPv6 和自动地址族选择
- 通过配置结构设置 `setsockopt(2)` 选项

## OHOS 适配

- 上游使用无依赖的 Makefile，配方以 `-std=c99` 编译并产出 `libsocket99.a`。
- 配方从 Conan `tools.build:compiler_executables` 获取编译器和归档工具，避免依赖未定义的 shell 环境变量。
- 版本补丁补齐公共头文件对 `size_t` 与 `FILE` 的直接声明，使 `#include <socket99.h>` 可独立编译。
- 上游 `make test` 的本地 Unix-domain 路径使用测试工作目录中的 `test_foo`，设备验证在用户可写工作区执行。

## 依赖关系

- 编译依赖：C99 编译器和 POSIX socket API；无 Conan 依赖。
- 运行时依赖：HarmonyOS 系统 libc/socket 接口。

## 参考资料

- [上游仓库](https://github.com/silentbicycle/socket99)
- [上游 README](https://github.com/silentbicycle/socket99/blob/master/README.md)
