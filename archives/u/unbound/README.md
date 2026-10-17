# unbound

Unbound 是 NLnet Labs 开发的验证型（validating）、递归式（recursive）、缓存型 DNS 解析器，支持 DNSSEC 验证，附带 `libunbound` 解析器库与 `unbound`/`unbound-checkconf`/`unbound-control`/`unbound-host`/`unbound-anchor` 命令行工具。

## 功能概述

- 递归与缓存 DNS 解析（forwarder / stub / recursive 模式）
- DNSSEC 验证（RFC 4033-4035），支持 DNS over TLS
- `libunbound` C 库：嵌入式解析器 API（`ub_ctx_create`/`ub_resolve` 等）
- 命令行工具：`unbound`（守护进程）、`unbound-checkconf`（配置校验）、`unbound-control`（运行时管理）、`unbound-host`（查询工具）、`unbound-anchor`（信任锚管理）
- 插件模块体系：validator / iterator / dns64 / respip

## OHOS 适配

本适配基于官方 1.22.0 上游，native 编译到 `aarch64-unknown-linux-ohos`（autotools），关键适配点（详见 `1.22.0/notes.md`）：

- **E007**：`config.guess`/`config.sub` 补丁，识别 `__OHOS__`/HarmonyOS 三元组
- **E129**：configure 临时目录 `umask 077→022`，规避 HMDFS setgid 目录权限
- **E119**：`conanfile.py` 在 OHOS 上注入 `-D_UAPI_LINUX_SOCKET_H`（R8：禁止补丁 `#ifdef __OHOS__`），跳过 `linux/net_tstamp.h` 与 SDK `sockaddr_storage` 重复定义
- **E002**：testcode 临时文件改 `getenv("TMPDIR")`（鸿蒙 `/tmp` 只读）
- `-flto` 在 clang 上链接极慢 → `--disable-flto`

## 依赖关系

- **编译/运行依赖**：`openssl/3.5.6.1`、`libevent/2.1.12`、`expat/2.8.2`（ohpcd Conan 制品仓）
- 可选依赖 `nghttp2`/`protobuf-c`（HTTP2 支持）制品仓无配方，默认关闭
- 扩展集成测试 `make longtest` 需外部工具 `ldns-testns`（ldns 包），环境中缺失

## 参考资料

- 官网: https://www.nlnetlabs.nl/projects/unbound/about/
- 源码: https://www.nlnetlabs.nl/downloads/unbound/
- 文档: https://unbound.docs.nlnetlabs.nl/
- 许可证: BSD-3-Clause
