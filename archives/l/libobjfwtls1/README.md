# libobjfwtls1

ObjFWTLS is the TLS support library of ObjFW (Objective-C, OpenSSL backend),
providing OFTLSStream / OFX509Certificate for TLS clients and servers.

## OHOS adaptation

- Builds the whole official ObjFW source tree with its shipped Autotools files
  (in-source build, serialized `make -j1` for the HMDFS jobserver limit).
- Enables TLS explicitly with `--with-tls=openssl` against the published
  `openssl/3.5.8.1` package; the configure probe uses plain `-lssl -lcrypto`,
  wired via `AutotoolsDeps`.
- Keeps upstream source behavior and the `libobjfwtls.so.1` ABI unchanged.
- Uses package-relative install layout and omits the obsolete `.la` files.
- Runs the upstream `make check` suite (ObjFW OFTests framework, offline-safe:
  HTTP client tests use a local 127.0.0.1 server).
- Runs installed-package consumers: an Objective-C test calling the real
  OFX509Certificate API plus a C test for the ObjFW runtime linkage.

## Dependencies

- `openssl/3.5.8.1` supplies libssl/libcrypto for the TLS backend.

## References

- https://objfw.nil.im/
- https://objfw.nil.im/downloads/objfw-1.5.7.tar.gz
