# pgpool-II — PostgreSQL Connection Pooling Middleware

pgpool-II is a middleware that sits between PostgreSQL servers and their
clients, providing connection pooling, load balancing, replication, and
query caching capabilities.

## OpenHarmony/HarmonyOS Port Status

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 4.7.2 | published | 2026-06-12 | Requires -D__MUSL__ CFLAGS, configure umask fix |

## Key Adaptation Notes

- **HMDFS filesystem**: SGID inheritance + umask 077 conflict requires
  configure patch to remove umask from temp dir creation
- **__MUSL__ macro**: OHOS SDK doesn't define __MUSL__ but uses it in
  sys/socket.h headers; must add -D__MUSL__ to CFLAGS
- **CONFIG_SHELL**: Must use bash explicitly (not zsh/sh) to prevent
  autoconf ECHO misdetection
- **Platform detection**: config.guess/config.sub need HarmonyOS detection

## Dependencies

- PostgreSQL (headers for configure check)
- libbsd >= 0.11.7
- libmd >= 0.1.0
