# authbind

Allows non-root programs to bind() to low ports, without any changes to the application.

This is achieved with LD_PRELOAD: the `authbind` wrapper sets `LD_PRELOAD` to
`libauthbind.so`, which intercepts `bind()` via `dlsym(RTLD_NEXT, ...)` and
asks the setuid `helper` whether the caller is permitted to bind the requested
address/port (checked against `/etc/authbind/byport`, `/etc/authbind/byaddr`,
`/etc/authbind/byuid`).

- 上游: Debian source package（Ian Jackson） https://tracker.debian.org/authbind
- 版本: 2.2.0（2024-11-11）
- 构建: 纯 Makefile（无 configure），仅依赖系统 libc/libdl
- 许可证: GPL-2.0-or-later
