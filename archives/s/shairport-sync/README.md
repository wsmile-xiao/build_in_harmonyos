# shairport-sync

Shairport Sync is an AirPlay audio player — it plays audio streamed from Apple devices (iPhone, iPad, Mac) and other AirPlay-compatible sources.

## Description

Shairport Sync receives AirPlay audio streams and plays them through the local audio output. It supports the classic AirPlay 1 protocol and can be configured for AirPlay 2 with additional dependencies. This archive provides the **shairport-sync binary** built for OpenHarmony aarch64.

## Features

- AirPlay 1 (classic) audio receiver
- ALSA audio output backend
- Soxr high-quality audio resampling
- OpenSSL-based AirPlay encryption
- Avahi mDNS service discovery

## Version History

| Version | Status | Date |
|---------|--------|------|
| 5.0.4 | built | 2026-05-26 |

## OpenHarmony Adaptation Notes

- Platform: aarch64-unknown-linux-ohos
- Build system: autotools
- pthread_cancel not available on OHOS/musl — uses compatibility shim (ohos_compat.c)
- Requires: OpenSSL, soxr, alsa-lib, avahi

## Links

- Homepage: https://github.com/mikebrady/shairport-sync
- Source: https://github.com/mikebrady/shairport-sync/archive/refs/tags/5.0.4.tar.gz