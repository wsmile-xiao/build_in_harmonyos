# massdns

高性能 DNS 批量解析工具 — 针对需要解析大量域名（百万甚至十亿级）的场景。

- **主页**: https://github.com/blechschmidt/massdns
- **许可证**: GPL-3.0-only
- **构建系统**: Makefile（纯 C，无 configure，无 make install）
- **功能**: 高性能 DNS stub resolver，支持批量域名解析、IPv4/IPv6、自定义 DNS 服务器
- **特性**: 基于 Linux epoll 机制的高并发 DNS 查询，支持多种输出格式（文本、JSON、二进制、域名列表）
