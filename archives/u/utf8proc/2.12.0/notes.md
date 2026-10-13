# utf8proc/2.12.0

- Upstream release: `v2.12.0`, official archive SHA-256 `a393fbef160835fb315bc3e91ba8d86f7a73a7cec9e6198b6c60b848b498bfeb`.
- The recipe enables `UTF8PROC_ENABLE_TESTING` for native builds and rejects a missing or empty CTest registration. Windows cross builds compile the target package and consumer without executing AArch64 binaries.
- On the authorized OHOS PC, separate private native Conan creates for static and shared packages returned 0. Each registered and passed 10 upstream CTest tests; each installed-package consumer passed 11 checks. Raw static log SHA-256: `82e54369453d17c0c4537815392bfcdfc2d5c1313517887c850d1b7c7ef48d6b`; shared log SHA-256: `4b2c17c8a25c1a36987726abf6ce806b373d5d17daf90c6842958095e107d7fb`.
- Direct Windows-to-OHOS SDK smoke builds produced an AArch64 static archive and shared ELF. The installed static archive consumer compiled and linked as AArch64 ELF. These direct builds are separate from the native Conan creates.
- `LICENSE.md` is packaged in full, preserving both MIT and Unicode data notices.
- Formal W3 receipt, software PR, platform CI, maintainer acceptance, and points are pending.
