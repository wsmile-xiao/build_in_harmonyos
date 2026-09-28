# librecast

Librecast — fast, efficient and scalable communication by leveraging IPv6 multicast (the Librecast IPv6 multicast library).

## Homepage
https://librecast.net/librecast.html (upstream: https://codeberg.org/librecast/librecast, mirror: https://git.sr.ht/~librecast/librecast)

## License
GPL-2.0-only OR GPL-3.0-only

## Build System
Autotools (configure + make). Upstream ships a hand-written `src/Makefile.in` that only builds the shared object
(`all: $(SOFILES)`) — there is no static build target.

## Dependencies
- `lcrq/0.4.1` — RaptorQ FEC; `include/librecast/net.h` includes `<lcrq.h>` (public require)
- `libsodium/1.0.22` — encryption/hashing; `include/librecast/crypto.h` includes `<sodium.h>` (public require)
- System: pthread, m, dl
- Bundled (not separate packages, built by the top-level configure):
  - `libs/blake3` — BLAKE3 reference C implementation → static `libblake3.a`
  - `libs/libmld` — MLDv2 listener, built via `AC_CONFIG_SUBDIRS` and linked into `liblibrecast.so`

## OHOS Adaptation
- **E007** — the bundled `config.guess` (2022-05-25) cannot recognise HarmonyOS. Patched for both the top level and
  the nested `libs/libmld` copy. `config.sub` additionally needed `linux-ohos*` in its kernel-os validation table
  (the E007 patch script does not add that combination).
- **E129/E114** — `configure` and `libs/libmld/configure` create their config.status temp dir with
  `umask 077 && mktemp -d`. On setgid HMDFS mounts that yields `drwx--S---` and config.status aborts with
  `subs1.awk: Permission denied`. Both switched to `umask 022`.
- **E091** — `libs/libmld/src/mld.c` includes `<linux/netlink.h>`, whose kernel UAPI copy of
  `struct sockaddr_storage` collides with musl's `<sys/socket.h>`. Renamed around those includes.
- **`uname -s` = HarmonyOS** — `src/Makefile` selects the interface implementation with
  `ifeq ($(OSNAME),Linux)`, so HarmonyOS fell through to the stub `if.o` (no `lc_tuntap_create`).
  `Makefile.in` now normalises HarmonyOS to Linux.
- **E127 (pthread_cancel)** — musl has no working thread cancellation: the OHOS device libc exports
  `pthread_cancel` but it returns `ENOSYS`, `pthread_setcanceltype` is absent, and the cross sysroot libc does not
  export any of them, so `liblibrecast.so` could not even be relocated. The library's thread teardown is rewritten
  to cooperative shutdown (NULL-job stop sentinels for the smolq/mld queues, stop flags plus `shutdown()`/socket
  close to release blocking `recvmsg()`), and callers use `q_pool_stop()`.
- **RFC 3542 `inet6_opt_*`** — musl never implemented the hop-by-hop/destination option builders that
  `libs/libmld/src/mld.c` calls, and OHOS has no provider anywhere (SDK headers, sysroot libc, device libc).
  A conforming implementation (same bytes as glibc/FreeBSD, transcribed from the KAME reference) is compiled in.
- Upstream tarball contains dangling symlinks (`test/**/*.test`, resolved at build time) — incompatible with
  `shutil.copytree` on HMDFS; `.work` is rebuilt with Python `tarfile` preserving symlinks.
- In-source build only (no VPATH; `src/Makefile` links `../libs/libmld/src/*.o` by relative path) — the recipe uses
  `basic_layout(self, build_folder=".")`.
- Source mirror: codeberg.org rate-limits CI workers (HTTP 429); source fetched from `git.sr.ht` mirror.

## Versions
- 0.11.2 — adapted 2026-09-26. Conan recipe depends on `lcrq/0.4.1` + `libsodium/1.0.22`; 25 portability patches;
  test_package consumer test exercises `lc_ctx_new`/`lc_channel_new`/`lc_socketpair` lifecycle.
  See `0.11.2/notes.md`.
- 0.8.0 — built 2026-09-24. `conan-verify` G0-G4 + L2/L4/L5 all PASS; artifacts `dlopen` on device with no
  `LD_PRELOAD`; test_package consumer test 20/20.
  Upstream tests: nested `libs/libmld` suite 10 run / 8 OK / 2 WARN / 0 FAIL;
  top-level runnable subset (31 cases needing real POSIX thread cancellation excluded) 38 OK / 7 WARN /
  4 FAIL (pre-existing `falloc` SIGABRT) / 31 SKIP / 0 HANG. See `0.8.0/notes.md` and `0.8.0/reports/`.
