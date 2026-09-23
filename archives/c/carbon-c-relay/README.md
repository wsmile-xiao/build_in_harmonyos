# carbon-c-relay

集群感知的 Graphite 指标中继/路由器（C，Apache-2.0）。

- 上游: https://github.com/grobian/carbon-c-relay
- 产物: `relay`（应用二进制，支持 TCP/UDP/unix 多协议监听、一致性哈希、
  聚合、重写、failover、gzip 压缩传输）
- 本仓库适配版本: 3.7.3（见 `3.7.3/` 子目录）

## OHOS 适配要点

- 名义交叉三元组 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`
  （E007，config.guess/config.sub 已随补丁升级）；
- configure 的 `(umask 077 && mktemp)` 在 HMDFS 下需移除（E011/E114）；
- 平台限制：执行环境对 AF_UNIX bind 返回 EPERM，unix socket 监听功能
  不可用；TCP/UDP 转发、聚合、重写、configtest 均正常（详见 3.7.3/notes.md）。
