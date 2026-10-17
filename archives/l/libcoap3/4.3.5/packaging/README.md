# libcoap3 4.3.5 打包说明

## 产物清单（conan create 自动打包）

- `lib/libcoap-3.a` — CoAP 协议库静态库（DTLS/openssl、TCP/WebSocket、OSCORE、Q-Block、epoll 全特性）
- `include/coap3/*.h` — 公共 API 头文件（coap.h 总入口）
- `lib/cmake/libcoap/libcoapConfig.cmake` — 上游 CMake 导出配置（target: `libcoap::coap-3`）

## 使用方式

```bash
conan install --requires=libcoap3/4.3.5 -pr=ohos-aarch64
```

CMake 消费：
```cmake
find_package(libcoap REQUIRED)
target_link_libraries(app PRIVATE libcoap::coap-3)
```

依赖链由 Conan 自动解析：openssl/3.5.6（DTLS 加密后端）。

## 命令行工具

无（ENABLE_EXAMPLES=OFF，本包仅提供库）。
