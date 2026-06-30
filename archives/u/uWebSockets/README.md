# uWebSockets

**描述**: Simple, secure & standards compliant web server for the most demanding of applications.

高性能 C++ WebSocket/HTTP 库，header-only 设计，底层使用 uSockets 异步网络库。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 18 (v18.20.0) | built (功能验证通过) | HTTP ✅ WebSocket ✅ SSL ✅ |

## 依赖

- uSockets >= 0.7.1
- OpenSSL >= 3.0
- zlib >= 1.2

## 鸿蒙适配状态

- ✅ 编译成功 (clang 15.0.4, C++20)
- ✅ 功能测试通过 (HTTP/WebSocket/SSL 全部正常)
- ✅ 8 个官方示例全部可执行
- ✅ 头文件安装到 ~/usr/local/include/uWebSockets/

## 使用方法

```cpp
#include "uWebSockets/App.h"

uWS::App().get("/*", [](auto *res, auto *req) {
    res->end("Hello from HarmonyOS!");
}).listen(9001, [](auto *token) {
    if (token) std::cout << "Listening on 9001" << std::endl;
}).run();
```

编译:
```bash
clang++ -std=c++17 -I ~/usr/local/include \
    your_app.cpp ~/usr/local/lib/uSockets.a \
    -lssl -lcrypto -lz -lpthread
```
