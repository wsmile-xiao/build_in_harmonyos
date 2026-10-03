# merecat

merecat is a small, made-easy HTTP/HTTPS server based on Jef Poskanzer's thttpd,
maintained by Joachim Wiberg (troglobit). It also ships the `htpasswd` helper for
managing `.htpasswd` password files.

- Homepage: <https://github.com/troglobit/merecat>
- License: BSD-2-Clause
- Package type: command-line application (HTTP/HTTPS server + htpasswd tool)
- CI note: the pinned source is the upstream git snapshot that Debian packaged as
  `2.31+git20260330+ds-1` (commit `57a2ce7c0cca`, 2026-03-15). The git snapshot ships no
  generated `configure`, so the recipe bootstraps Autotools with `automake/1.18` from the
  OHOS registry and runs the full upstream `make check` suite (14 registered tests) inside
  `build()`. On HarmonyOS PC two source patches are applied: permission checks fall back to
  `access(2)` because HMDFS never exposes the POSIX "other" bits, and `tempfile()` honours
  `$TMPDIR` because `/tmp` is read-only.
