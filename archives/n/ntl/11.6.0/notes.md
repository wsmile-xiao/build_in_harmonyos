# NTL 11.6.0 HarmonyOS PC adaptation

- Builds the static NTL C++ number theory library with NTL's portable internal long-integer backend.
- Disables native CPU tuning and uses conservative ARM/POSIX feature values.
- Keeps configure compile/link probes but skips executing OHOS target binaries on the build host.
- Disables the optional GMP and GF2X backends to keep the dependency surface focused.
- Adds a consumer test that performs real arbitrary-precision arithmetic.

Local verification covers recipe syntax, metadata, patch applicability, source checksum, and repository static gates. The official OHOS armv8 pipeline remains authoritative for the cross-build result.
