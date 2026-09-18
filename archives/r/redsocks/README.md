# redsocks 0.5 for HarmonyOS

redsocks is a transparent TCP-to-proxy redirector.

## Software Info
| Item | Value |
|------|-------|
| Name | redsocks |
| Version | 0.5 |
| Source | https://github.com/darkk/redsocks |
| License | Apache-2.0 |
| Build | Makefile |

## Dependencies
| Dep | Version | Source |
|-----|---------|--------|
| libevent | 2.1.12 | Conan ohpcd |

## Build
```bash
make CC=clang LIBS=\'-levent\' -j1
```

## Notes
- Override LIBS=-levent (Conan provides aggregated event lib, not event_core)
- config.h via uname: OHOS=Linux -> USE_IPTABLES
- gen/version.c non-git fallback: redsocks/0.5
