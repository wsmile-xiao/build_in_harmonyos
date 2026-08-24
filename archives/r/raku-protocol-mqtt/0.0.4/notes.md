# Protocol::MQTT 0.0.4 HarmonyOS PC adaptation notes

## Upstream

- Repository: https://github.com/Leont/raku-protocol-mqtt
- Distribution: https://raku.land/zef:leont/Protocol::MQTT
- Fixed source SHA256: `ff401f199aa73a73382bcee4ac6b1e78a0fa77fac68d6b75cf0b02d173052294`

The release metadata points to the immutable zef ecosystem archive. The module declares no third-party Raku dependencies and requires Raku language level v6.d.

## Compatibility patch

The 0.0.4 distribution still declared `Protocol::MQTT:ver<0.0.3>` in its compilation unit. The patch aligns that declaration with the release metadata so version-constrained consumers can import 0.0.4. It also enforces MQTT 3.1.1 section 2.2.3's four-byte limit for Remaining Length fields, preventing unbounded malformed-field decoding.

## Tests

All four upstream test files run separately during `build()` without changes or exclusions, covering 185 assertions.

The consumer test imports exactly `Protocol::MQTT:ver<0.0.4>` through `RAKULIB`, checks complete CONNECT and QoS 1 PUBLISH wire encodings, decodes the PUBLISH packet, verifies topic-filter matching, and rejects a malformed five-byte Remaining Length field (10 checks).

## Dependency status

`moarvm/2025.11`, `nqp/2025.11`, and `rakudo/2025.11` are published on the competition Conan Remote. The formal W3 build consumes the published `rakudo/2025.11` OHOS arm64 package rather than a local dependency build.

## Adaptation path

Path A only. The package-specific version and MQTT parser fixes do not establish a new cross-library HarmonyOS technique, so no Path B knowledge draft is claimed.
---

**编译结束**: 2026-08-23 01:53
**最终状态**: built
