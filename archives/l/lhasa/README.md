# lhasa

Lhasa is a command-line tool for extracting LHA archives (.lzh, .lzs) and a C library (liblhasa) for reading LHA archive files. It supports multiple compression methods used in the LHA format, including LH1, LH5, LH6, LH7, LHX, LK7, LZ5, LZS, PM1, and PM2.

## OHOS adaptation

- Pure C library with no external dependencies
- Builds with autotools (autoconf, automake, libtool)
- Requires `--build=aarch64-unknown-linux-gnu` since config.guess doesn't recognize HarmonyOS
- HMDFS workaround: use `CONFIG_SHELL=/bin/sh` to avoid bash's `getcwd()` failure on symlink paths
- HMDFS workaround: patch `umask 077` to `umask 0` since HMDFS `chmod` is a no-op
- 3 compiled upstream tests pass; 14 shell-based tests fail due to HMDFS shell limitation

## Dependencies

None. Only requires standard C library and autotools toolchain.

## References

- https://fragglet.github.io/lhasa/
- https://github.com/fragglet/lhasa