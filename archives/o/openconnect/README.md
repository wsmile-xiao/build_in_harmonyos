# openconnect

## 简介

openconnect 是 OpenConnect VPN（及 Cisco AnyConnect、Juniper/Pulse、GlobalProtect）协议的客户端，ocserv 的姊妹项目。它提供 SSL VPN 隧道连接、证书/令牌认证、DTLS 低延迟通道和 ESP 加密支持。

产物为可执行文件：`openconnect`（VPN 客户端主程序），同时安装 libopenconnect API 头文件（`openconnect.h`）供下游集成（如 ocserv 上游测试套件）。

## OHOS 适配

- **构建系统**：autotools（官方 infradead.org release tarball，自带预生成 configure）
- **依赖策略**：gnutls/3.8.10、libxml2/2.15.3、zlib/1.3.1 来自 ohpcd 制品仓（W0 实测就绪）；可选依赖 lz4/libproxy/stoken/libpcsclite/libpskc/gssapi/java 全部 `--without`（制品仓未发布，核心 VPN 功能不受影响）
- **关键适配**：
  1. `<linux/tcp.h>` 与 `<sys/socket.h>` 的 `sockaddr_storage` 重定义（OHOS musl）→ `__OHOS__` 下改用 `<netinet/tcp.h>`（TCP_INFO/struct tcp_info 均可用）
  2. musl 不间接引入 `<stdlib.h>` → 8 个源文件显式补 include（上游 `-Werror-implicit-function-declaration` 拦截）
  3. 2020 版 ltmain.sh + autoconf 2.72 的 libtool 引号损坏 → 配方内 `_fix_libtool_quoting()` 修复
  4. config.status umask 077 → HMDFS 临时目录权限失败（`_fix_config_status()`）
  5. 依赖包 .la 路径残留 → `_fix_dependency_la_paths()` 重写（cattle-1.0 先例）
  6. ELF 签名（binary-sign-tool -selfSign）

## 可选依赖禁用清单

lz4 / libproxy / stoken / libpcsclite / libpskc / gssapi / java 全部 disabled（ohpcd 制品仓未发布对应包）。HOTP/TOTP 软件 token 由内置 oath.c 提供不受影响；DTLS/ESP 加密完整保留。

## 验证

```bash
openconnect --version
# OpenConnect version v8.10-unknown
# Using GnuTLS 3.8.10. Features present: HOTP software token, TOTP software token, System keys, DTLS, ESP
# Supported protocols: anyconnect (default), nc, gp, pulse
```

上游测试：`make check` 3/3 PASS（autocompletion / lzstest / seqtest）。

## 参考

- 官网: https://www.infradead.org/openconnect/
- 源码: https://www.infradead.org/openconnect/download/openconnect-8.10.tar.gz
