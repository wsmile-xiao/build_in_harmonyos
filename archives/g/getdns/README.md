# getdns

现代异步 DNS API 的 C 实现（getdnsapi 系）：libgetdns 库支持 DNSSEC 验证、
DNS-over-TLS，附带 getdns_query / getdns_server_mon 命令行工具。

- 上游：https://github.com/getdnsapi/getdns（tag v1.7.3）
- 构建系统：CMake
- 适配：HarmonyOS PC (aarch64-unknown-linux-ohos)，clang 15
- 模式：STUB 解析（ENABLE_STUB_ONLY=ON），事件循环扩展 libev/libevent2/libuv

## 版本索引

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.7.3 | published | 首次适配：CMake + stub-only + 三事件循环扩展 + Check 测试框架全跑 |
