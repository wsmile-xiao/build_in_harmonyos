# chinadns-c

ChinaDNS-C —— DNS 分流工具。根据 chnroute 中国 IP 列表把域名解析请求
分流：国内域名走国内 DNS（如 114.114.114.114），其他域名走可信 DNS
（如 OpenDNS 208.67.222.222:443），解决 DNS 污染问题。纯用户态 C 实现，
无外部依赖（仅需 libc）。

- 上游：https://github.com/clowwindy/ChinaDNS-C
- 许可证：GPL-3.0
- 类型：命令行工具（bin/chinadns）

## 已适配版本

| 版本 | 状态 | 构建系统 |
|------|------|----------|
| 1.3.2 | built | autotools（generated-build 快照） |
