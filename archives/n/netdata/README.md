# Netdata

Real-time performance monitoring, health, and visualization for systems and applications.

- **Homepage**: https://www.netdata.cloud
- **License**: GPL-3.0
- **Build system**: CMake

## OHOS Adaptation

### Patches
1. `0001-CMakeLists.txt.patch` — Add OpenHarmony platform detection (catch-all FATAL_ERROR for unknown platforms kept) and CMake feature checks: pthread affinity (HAVE_PTHREAD_SETAFFINITY_NP), thread cancellation (HAVE_PTHREAD_SETCANCEL), libuuid (with verified arc4random_buf fallback when absent)
2. `0002-src-collectors-proc.plugin-proc_stat.c.patch` — Guard CPU affinity APIs with `HAVE_PTHREAD_SETAFFINITY_NP` (pthread_setaffinity_np/getaffinity_np not provided by OHOS musl)
3. `0003-packaging-cmake-config.cmake.h.in.patch` — Expose the new feature-check results via config.h
4. `0004-src-libnetdata-threads-threads.c.patch` — Guard pthread_setcanceltype/pthread_setcancelstate with `HAVE_PTHREAD_SETCANCEL` (not provided by OHOS musl; netdata does not use pthread_cancel)
5. `0005-src-libnetdata-os-uuid_generate.c.patch` — Fall back to arc4random_buf-based RFC 4122 v4 UUID generation when libuuid is unavailable (`HAVE_LIBUUID` detection)

All C-code guards use build-time feature detection macros (no platform conditionals in C code).

### Disabled Features
Features disabled due to OHOS platform limitations:
- `ENABLE_PLUGIN_EBPF` — eBPF not available on OHOS
- `ENABLE_PLUGIN_GO` — Go runtime not available
- `ENABLE_PLUGIN_FREEIPMI` — IPMI library not available
- `ENABLE_PLUGIN_CUPS` — CUPS printing not available
- `ENABLE_PLUGIN_SYSTEMD_JOURNAL` — systemd not available on OHOS
- `ENABLE_PLUGIN_APPS` / `ENABLE_PLUGIN_DEBUGFS` — libcap/capabilities not available
- `ENABLE_PLUGIN_XENSTAT` / `ENABLE_PLUGIN_NFACCT` — Xen/Netfilter not applicable
- `ENABLE_H2O` — libh2o submodule empty in release tarball
- `ENABLE_CLOUD` / `ENABLE_ACLK` — Cloud features require network infrastructure
- `ENABLE_ML` — Machine learning framework not available
- `ENABLE_WEBRTC` / `ENABLE_SENTRY` — Optional features not available

### Dependencies
- openssl/1.1.1w
- zlib/1.3.1
- lz4/1.10.0
- libuv/1.52.1
- json-c/0.18
- libyaml/0.2.5
- protobuf/33.6.1
- pcre2/10.40 (log2journal; also shields against broken system libpcre2-8.pc on some workers)
- sqlite3 (embedded in source)
