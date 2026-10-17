# rdma-core

RDMA core userspace libraries and daemons for Linux InfiniBand/RDMA subsystem.

Provides:
- **libibverbs** — RDMA verbs API
- **librdmacm** — RDMA connection manager
- **libibumad** — InfiniBand MAD library
- **libibmad** — InfiniBand MAD library
- **libibnetdisc** — InfiniBand network discovery
- **infiniband-diags** — diagnostic tools

## OHOS Adaptation

Optional features disabled for HarmonyOS PC:
- `ENABLE_RESOLVE_NEIGH=0` — no libnl dependency
- `NO_PYVERBS=1` — no Python bindings (Cython)
- `NO_MAN_PAGES=1` — no man pages (pandoc)
- `NO_COMPAT_SYMS=1` — no GNU symbol versioning (musl libc)
- `ENABLE_VALGRIND=0` — no valgrind annotations

## Source

- Homepage: https://github.com/linux-rdma/rdma-core
- License: GPL-2.0 OR BSD-2-Clause
