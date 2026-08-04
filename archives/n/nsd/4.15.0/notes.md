# NSD 4.15.0

- Builds the authoritative DNS server and validation utilities with the
  published OpenSSL package.
- Optional dnstap, systemd, XDP, external libevent, recvmmsg, TCP Fast Open,
  and x86 SIMD kernels are disabled for a portable OHOS build.
- The official 4.15.0 release tarball omits `tpkg`, and its `make test` target
  is intentionally empty. The consumer checks the version, parses a minimal
  configuration, and validates a real zone file.
- Local OHOS arm64 `conan create` completed successfully: OpenSSL, NSD, and
  five packaged NSD tools were built for AArch64. The three consumer checks
  were prepared by the test package; runtime execution is not applicable
  locally because no OHOS arm64 HDC target is connected.
- Native OHOS builds use the worker `TMPDIR` and the repository's E011
  `umask 022` workaround for Autoconf temporary directories and files, so
  `config.status` can create and read its generated awk programs on HMDFS.
- Official OHOS test and CI results remain pending.
