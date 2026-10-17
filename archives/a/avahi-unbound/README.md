# avahi-unbound

为 unbound DNS 解析器提供 avahi mDNS 集成配置文件。

## 功能概述

- 配置 unbound 将 `.local` 区域查询转发至 avahi-daemon 的 DNS 代理（127.0.0.1:5354）
- 允许 unbound 查询 localhost（转发目标）
- 将 `.local` 域标记为 insecure（mDNS 不支持 DNSSEC）

## OHOS 适配

- **纯配置包**：无编译步骤，不产出二进制或库文件
- 配置文件内容源自 Alpine Linux aports 仓库（`main/avahi/unbound.conf`）
- 使用 avahi v0.9-rc5 源码 tarball 做版本一致性校验（与 `avahi-compat-libdns_sd` / `avahi-glib` 同源）
- 安装 `etc/unbound/unbound.conf.d/avahi.conf`
- 上游无测试用例（配置文件不在 avahi 源码中），test_package 提供 7 个自定义断言验证配置文件内容

## 依赖

- unbound 1.22.0（运行时依赖）

## 参考资料

- 上游仓库：https://github.com/avahi/avahi
- Alpine aports：https://github.com/alpinelinux/aports/tree/master/main/avahi
- 版本：0.9-rc5（tag v0.9-rc5）
