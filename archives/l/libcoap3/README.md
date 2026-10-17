# libcoap3

## 简介

libcoap 是 CoAP（Constrained Application Protocol，RFC 7252）的 C 语言实现，面向受限设备的轻量级物联网应用协议库。支持 DTLS 加密（openssl/gnutls/mbedtls/tinydtls 后端）、TCP/WebSocket 传输、OSCORE 对象安全（RFC 8613）、Q-Block（RFC 9177）、观察者持久化与 epoll。

## OHOS 适配

- **版本**: 4.3.5（上游 tag v4.3.5，家族首次入仓）
- **构建系统**: CMake（上游双支持 autotools/cmake）
- **依赖**: openssl/3.5.6（DTLS 后端）
- **产物**: libcoap-3.a（静态）、include/coap3/、libcoapConfig.cmake（target: libcoap::coap-3）
- **平台补丁**: 无（纯 C 库，clang15 交叉编译一次通过）

## 测试

上游 CUnit 测试套 testdriver：16 套件 176 测试 1378 断言，arm64 鸿蒙原生运行全绿（176/176）。消费者级 test_package 验证 API：coap_startup/cleanup、coap_package_version、PDU 构造（init/token/option）、coap_split_uri、coap_new_context。

## 依赖

- openssl/3.5.6
