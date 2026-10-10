# isc-kea

ISC Kea 的 **DHCP/DNS 服务器套件本体**，适配 HarmonyOS PC（OHOS aarch64）。

## 是什么

ISC Kea 是现代 DHCPv4/DHCPv6 服务器与 DDNS 更新器套件。本包交付 3.0.3 的服务器本体：

- `kea-dhcp4` / `kea-dhcp6` —— DHCPv4/DHCPv6 服务器（租约分配、host reservations、
  RADIUS/TLS、高可用 hook 生态）
- `kea-dhcp-ddns` —— RFC 4703 动态 DNS（DDNS）请求处理与转发
- `kea-ctrl-agent` —— 控制 Agent，暴露 RESTful 管理 API（CA，支持 TLS 与 basic auth）
- `kea-lfc` —— 租约文件清理器（Lease File Cleaner）
- `keactrl` —— 服务启停/状态管理脚本
- 23 个核心 `libkea-*` 共享库（dhcp/dhcpsrv/cc/dns/asiolink/hooks/http/tcp/log 等），
  守护进程的运行闭包，同时可供嵌入式消费者链接（`include/kea` 公共头随包安装）

## OHOS 适配要点

- Kea 3.0 起由 Autotools 迁移到 **Meson**（单工程构建全树），配方按 ninja output path
  只编译本包目标（五守护进程 + 核心库 + 29 个上游测试套件可执行）
- 平台差异四处，方案与同族包（kea-hooks/kea-perfdhcp/kea-hook-*）一致：
  - meson 报 `system='harmonyos'` → 补丁归一化为 linux（`0001`）
  - musl/UAPI `sockaddr_storage` 冲突 → netlink 头 include 守卫（`0002`）
  - musl 无 `pthread_setcancelstate` → `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`
  - 配置期 compile-and-run 探针 → host 依赖 libdirs 注入 `LD_LIBRARY_PATH`
- mysql/postgresql/netconf/krb5 后端禁用（制品仓无对应包；kea-yang 仅经 netconf 可达）
- daemon 运行时流量验证受环境限制（需真实 socket/接口绑定）：以 24 lib + 5 bin 上游
  gtest 套件 + test_package（五守护进程 `--version` 实跑、API 链接断言、OHOS ABI/dlopen
  检查）覆盖

## 依赖关系

- 编译依赖：boost/1.85.0（钉住：1.90/1.91 缺 Kea 所需头）、log4cplus/2.2.0.1、openssl/3.5.8.1
- 测试依赖：gtest/1.17.0.1；构建工具：meson/1.11.0
- 同族拆分包：kea-hooks（hooks 框架库）、kea-hook-*（hook 插件）、kea-perfdhcp（性能客户端）、
  kea-shell（管理脚本）

## 参考资料

- 上游项目：https://gitlab.isc.org/isc-projects/kea
- 官网：https://www.isc.org/kea/
- 源码包：https://ftp.isc.org/isc/kea/3.0.3/kea-3.0.3.tar.xz
