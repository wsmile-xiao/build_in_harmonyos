# ocserv

## 简介

ocserv（OpenConnect VPN Server）是实现了 Cisco AnyConnect / OpenConnect SSL VPN 协议的 VPN 服务端。它性能好、内存占用低，支持密码/证书认证、IPv4/IPv6、虚拟主机等特性。

产物为可执行文件：`ocserv`（主服务）、`ocserv-worker`（工作进程）、`occtl`（管理 CLI）、`ocpasswd`（密码文件工具）。

## OHOS 适配

- **构建系统**：meson（1.5.0 上游已从 autotools 迁移）
- **依赖策略**：gnutls/3.8.10、libev/4.33、readline/8.3 来自 ohpcd 制品仓；talloc/llhttp/protobuf-c/pcl/ccan/inih 用上游源码树内 bundled 副本（与上游 CI 的 `-Dlocal-*=true` 一致）
- **关键适配**：
  1. OHOS musl 无 `getpass(3)` → ocpasswd 增加 `__OHOS__` 守卫的兼容实现（open /dev/tty + termios 关回显）
  2. CI/构建机无 protoc/protoc-c → 携带预生成 `ipc/ctl/cfg.pb-c.{c,h}`（protoc 3.21.12 + protoc-gen-c 1.5.2 生成），走 meson 的 `fs.exists` fallback 分支
  3. `tests/meson.build` 的 `test_base_deps` 缺 gnutls_dep（上游假设系统路径）→ 显式补齐
  4. `config-inherit` 测试硬编码 `/tmp`（OHOS 只读 E002）→ 尊重 `TMPDIR`
  5. ELF 可执行文件需 `binary-sign-tool` 签名后才能执行（E077）

## 可选依赖禁用清单

PAM/RADIUS/GSSAPI/liboath/libnl/maxmind/geoip/lz4/seccomp/systemd/utmp/libwrap/sock-diag/OIDC/compression/namespaces 全部 disabled（ohpcd 制品仓未发布对应包或平台不适用），核心 VPN 服务功能不受影响。

## 验证

```bash
ocserv --version       # OpenConnect VPN Server 1.5.0
ocpasswd --version     # ocpasswd - 1.5.0
occtl --help           # usage 输出
```

## 参考

- 官网: https://ocserv.openconnect-vpn.net/
- 源码: https://gitlab.com/ocserv/ocserv
