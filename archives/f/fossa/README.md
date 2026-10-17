# fossa

Cesanta Fossa — 嵌入式 C/C++ 异步网络库，在一个 event manager 上提供
HTTP/HTTPS/WebSocket/MQTT（客户端与 broker）/CoAP/DNS 客户端与服务端能力。
它是 Mongoose 6+ 的直接前身，符号前缀为 `NS_*`。

## 功能概述

- `ns_mgr` / `ns_connection` 事件循环，Linux/OHOS 上使用 epoll，其余平台回退 select
- HTTP 服务端（静态目录、SSI、digest auth、CGI）与客户端、WebSocket
- MQTT 客户端与 broker、CoAP、异步 DNS 解析与 DNS server
- 单文件合并产物：`fossa.c` + `fossa.h`

## OHOS 适配

- 构建系统：直接编译上游合并产物（`clang -fPIC` + `llvm-ar`），与
  `archives/m/mongoose/7.21` 同法；配方只使用 `settings`/`conf`，不读环境变量（R33）
- 交付静态库 `libfossa.a`：OHOS 用户态 `.so` 需 ELF 签名，`shared=True` 由
  `validate()` 明确拒绝
- 打包启用 `NS_ENABLE_COAP/IPV6/THREADS/MQTT_BROKER/DNS_SERVER`，与上游测试所覆盖的
  特性集一致；这些宏经 `cpp_info.defines` 下发给消费者，其中 `NS_ENABLE_IPV6`
  改变 `union socket_address` 布局，属 ABI 级宏，不可增删
- 无外部依赖：合并产物不含 zlib/frozen/cares，OpenSSL 仅在默认关闭的
  `NS_ENABLE_SSL` 下才需要
- 上游 `test/Makefile` 无条件链接 `-lssl` 的缺陷以补丁改为条件链接；
  依赖 POSIX 文件权限语义的分支改用上游自带 `TEST_UNDER_VIRTUALBOX` 开关处理

## 依赖关系

- 构建：clang、llvm-ar、make（`make -j1`）
- 运行：系统 pthread

## 验证结果

- OpenHarmony aarch64 真机 `conan create` 通过
- 上游单元测试：注册 60 例，实跑 58 例，55 通过 / 3 失败（均为环境或工具限制，
  已在 `2.1/notes.md` 与 `test_package/MANIFEST.yml` 逐条归因），断言合计 669
- Conan 消费测试（`test_package/test.c`）：4 例 15 断言全通过，含 127.0.0.1 上
  真实 HTTP 往返

## 参考资料

- 上游：https://github.com/cesanta/fossa
- 同族后继：https://github.com/cesanta/mongoose（本库上游已停止维护）
