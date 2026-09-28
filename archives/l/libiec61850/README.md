# libiec61850 — IEC 61850 protocol stack (MMS / GOOSE / Sampled Values)

libiec61850 is an open-source C implementation of the IEC 61850 standard used in
electric power automation. It provides both a client and a server side, covering
MMS (Manufacturing Message Specification), GOOSE (Generic Object Oriented Substation
Event) and Sampled Values over Ethernet, plus an optional TLS transport layer.

- **Homepage**: https://libiec61850.com/libiec61850
- **Source**: https://github.com/mz-automation/libiec61850
- **License**: LGPL-3.0
- **Build system**: CMake
- **Package type**: library (`libiec61850` + `hal`)

## Build variants

| Version | Status | Build date | Notes |
|---|---|---|---|
| 1.6.1 | built | 2026-09-26 | 首个 HarmonyOS PC 适配；见 `1.6.1/notes.md` |

## OHOS / HarmonyOS adaptation summary

- CMake needs `CMAKE_SYSTEM_NAME=Linux` because the device `uname` is `HarmonyOS`
  and CMake has no platform module for it (knowledge entry E092).
- One portability patch switches `hal/ethernet/linux/ethernet_linux.c` from
  `<linux/if_arp.h>` to the POSIX `<net/if_arp.h>` / `<net/if.h>` pair.
- No Conan dependencies. Optional bundled components (mbedtls / sqlite / winpcap)
  are not shipped in the official release tarball, so upstream itself disables the
  TLS, R-GOOSE/R-SMV, SNTP/TLS examples and the sqlite log driver.
