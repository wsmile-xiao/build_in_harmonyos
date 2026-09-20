# gdnsd

gdnsd is an authoritative-only DNS server with plugin-based geographic
(geo) balancing, failover, and more.

## OHOS 适配

- 版本: 3.8.2（官方 release tarball，自带预生成 configure 与 ragel 产物）
- 构建系统: autotools（configure/make，无需 autoreconf）
- 语言: C
- 依赖: libev、userspace-rcu、libsodium（conan 制品仓；zlib/openssl 上游未使用）

适配要点见 [3.8.2/notes.md](3.8.2/notes.md)。
