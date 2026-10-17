# nginx 1.26.2 — HarmonyOS Adaptation Notes

## Build System
nginx uses its own custom `./configure` script (not standard autotools or CMake).
The configure script generates `objs/Makefile` which is used by `make`.

## HarmonyOS OS Detection
- `uname -s` returns "HarmonyOS" on OHOS
- nginx's `auto/os/conf` only has cases for Linux, FreeBSD, Darwin, etc.
- Without patch: falls through to default case (no epoll, no sendfile)
- **Patch**: Add `HarmonyOS:*` case to `auto/os/conf` that sources `auto/os/linux`
- This enables: epoll, sendfile, sendfile64, EPOLLRDHUP, EPOLLEXCLUSIVE, etc.

## Dependencies
- **zlib/1.3.1**: Required for http_gzip_module (always enabled)
- **openssl/1.1.1w**: Required for http_ssl_module (--with-http_ssl_module)
- **PCRE2**: Found on system at `/data/service/hnp/pcre2.org/pcre2_10.47/`
  - nginx prefers PCRE2 over PCRE1
  - If PCRE2 not available, falls back to PCRE1 (libpcre)
  - PCRE is required for http_rewrite_module (always enabled)

## Configure Options
```bash
./configure \
  --prefix=/nginx \
  --with-http_ssl_module \
  --with-cc-opt="-I<zlib_include> -I<openssl_include>" \
  --with-ld-opt="-L<zlib_lib> -L<openssl_lib>" \
  CC=clang
```

## Build
```bash
make -j1
```

## Install
```bash
make install DESTDIR=$PACKAGE_FOLDER
# Installs to: $PACKAGE_FOLDER/nginx/sbin/nginx
```

## No Trimming
All default modules are enabled (no --without-* flags used):
- http_ssl_module (enabled via --with-http_ssl_module)
- http_rewrite_module (uses PCRE)
- http_gzip_module (uses zlib)
- http_proxy_module, http_fastcgi_module, http_uwsgi_module, http_scgi_module
- All upstream modules, etc.

## Test
nginx has no standard `make check` test suite. Smoke test: `nginx -V` outputs version.
---

**编译结束**: 2026-08-07 05:10
**最终状态**: built
