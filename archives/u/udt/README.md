# UDT

**描述**: UDP-based Data Transfer（UDT）— 基于 UDP 的高性能可靠应用层数据传输协议库，为高速广域网上的数据密集型应用而设计，传输速率显著优于 TCP。

UDT 完全运行于应用层，无需修改内核。其 API 与传统的 socket API 非常相似，现有 TCP 应用可以非常容易地改造为使用 UDT。同时支持可靠流（streaming）与部分可靠消息（messaging）两种模式，并支持自定义拥塞控制算法。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 4.11 | built | 库 libudt（.so/.a）+ 头文件 udt.h；上游自包含测试 4 例通过 |

## 功能

- 基于 UDP 的可靠流式数据传输
- 部分可靠（partial-reliable）消息传输
- 用户自定义拥塞控制算法
- 防火墙穿透 / NAT 打洞（rendezvous 连接）
- 与传统 socket API 高度相似的编程接口

## 依赖

- 无第三方编译依赖（仅使用系统 clang/clang++ 与 POSIX socket/pthread）

## 鸿蒙适配状态

- ✅ 编译成功（clang/clang++，aarch64，portable 微秒计时路径）
- ✅ libudt.so / libudt.a / udt.h 打包
- ✅ 上游自包含测试 app/test 的 4 个数据通路用例全部通过
- ✅ 消费者测试（test_package）在回环上实际收发数据验证 API

### OHOS 适配要点

- Makefile 默认使用 `g++`，配方中通过 `C++=clang++` 覆盖。
- 不能定义 `IA32`/`AMD64` 架构宏：UDT 的计时代码在这些宏分支下使用 x86 `rdtsc` 内联汇编，在 aarch64 上无法编译。不定义任何架构宏时，UDT 回退到 POSIX `getTime()` 微秒计时器（可移植路径）。
- 源码包根目录为 `udt4/`，构建时 `strip_root=True` 剥掉，`src/`、`app/` 位于顶层。

## 使用方法

```cpp
#include "udt.h"

UDT::startup();
UDTSOCKET sock = UDT::socket(AF_INET, SOCK_STREAM, 0);
// ... bind / listen / accept 或 connect
UDT::send(sock, buf, len, 0);
UDT::recv(sock, buf, len, 0);
UDT::close(sock);
UDT::cleanup();
```

编译:
```bash
clang++ your_app.cpp -ludt -lpthread -lm
```

## 参考资料

- 官网: https://udt.sourceforge.io/
- 官方源码发布: https://sourceforge.net/projects/udt/files/udt/4.11/
