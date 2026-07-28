# YAZ 5.37.3 adaptation notes

## Configuration

- Build static YAZ client/server libraries with XML support (XSLT disabled).
- Disable optional GnuTLS and ICU integrations until those dependencies are published for HarmonyOS PC.
- Disable TCP wrappers, Redis, memcached, and documentation toolchain discovery.
- Use Autotools dependency metadata generated from Conan packages.

## Verification

- Run all 44 upstream Automake tests under Conan's `VirtualRunEnv` so test executables can resolve packaged dependency libraries on the OHOS worker.
- The consumer test calls `yaz_version` and verifies version 5.37.3.
- Python syntax, recipe structure, source SHA-256, and whitespace are checked locally.
- The official OHOS armv8 pipeline remains authoritative for the full build result.
