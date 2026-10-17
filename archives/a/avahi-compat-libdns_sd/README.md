# avahi-compat-libdns_sd

基于 Avahi 的 Bonjour 兼容 DNS Service Discovery 库（`libdns_sd`），提供与
Apple Bonjour / mDNSResponder 兼容的 `dns_sd.h` API（`DNSServiceRegister`、
`DNSServiceBrowse`、`TXTRecord*` 等）。

## 功能概述

- `DNSService*` 系列：服务注册、浏览、解析、地址查询等 Bonjour API
- `TXTRecord*` 系列：TXT 记录编码/解码
- 与 mDNSResponder 的 `dns_sd.h` 头文件接口兼容，可替代 Bonjour SDK 使用

## OHOS 适配

- GitHub tag 源码包不含预生成 configure，需 `autogen.sh`（autoreconf）引导，
  构建期依赖 automake/libtool/gettext 工具（Conan tool_requires 提供）
- `avahi-client` 通过 D-Bus 与 avahi 守护进程通信，编译期依赖 dbus
- 仅构建 `avahi-common` / `avahi-client` / `avahi-compat-libdns_sd` 三个子目录，
  避免引入 libdaemon/expat 等守护进程相关依赖
- 上游测试（`make check`）仅 `txt-test` 与 `null-test` 两个用例，
  均为纯输入/编码测试，无需运行中的 avahi 守护进程

## 依赖

- dbus 1.14.10（编译依赖）

## 参考资料

- 上游仓库：https://github.com/avahi/avahi
- 版本：0.9-rc5（tag v0.9-rc5）
