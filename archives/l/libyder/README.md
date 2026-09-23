# libyder

Logging library for C applications (part of the babelouest/ulfius stack).

- Upstream: https://github.com/babelouest/yder
- License: LGPL-2.1-or-later
- Language: C99

## Supported log modes

- console (stdout)
- file
- syslog (OHOS libc provides syslog/openlog/closelog)
- callback
- journald — **disabled on OHOS** (no systemd journals; `WITH_JOURNALD=OFF`)

## Versions

| Version | Status |
|---------|--------|
| 1.4.20  | built (HarmonyOS PC, aarch64, static) |

## Dependencies

- Runtime: orcania (hard dependency)
- Test-build only: check (upstream CTest suite)
