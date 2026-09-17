# NRPE

NRPE（Nagios Remote Plugin Executor）是 Nagios 生态的远端监控代理组件，纯 C 实现，基于 autoconf/automake 构建。NRPE 由两部分组成：

- `nrpe`：守护进程，运行在被监控主机上，接收 check_nrpe 客户端的请求并在本地执行监控插件命令，结果通过 SSL 加密信道回传。
- `check_nrpe`：客户端，由 Nagios 服务器调用，与远端 nrpe 守护进程通信（支持 SSL/TLS，含匿名 DH 自动协商）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 4.1.3 | built | HarmonyOS PC（aarch64-linux-ohos）适配，openssl/3.5.8.1，tcp wrappers 裁剪 |

## 依赖

- openssl（硬依赖，SSL 加密传输；ohpcd 制品仓 openssl/3.5.8.1 已发布）
- tcp wrappers（可选，未发布 → --disable-tcpd）

## 关键适配点

- config.sub 补丁支持 ohos triplet；configure 4 处 umask 077 → 022（HMDFS）
- 详见 `4.1.3/notes.md` 与 `4.1.3/manifest.yaml`

上游：https://github.com/NagiosEnterprises/nrpe