# Target verification: shairplay 0.9.0-git20180824.096b61a

- Device: HarmonyOS PC aarch64, OHOS 6.0; Conan 2.29.1, Clang 15.
- Task run: `shairplay-w3-20260929T121145Z` on the current target endpoint, one launch, 12 final transaction receipts; frozen validator: `W3_PASS`.
- Source: official commit `096b61ad14c90169f438e690d096e3fcf87e504e`, SHA-256 `7e2b013ffe75ea2f13fb12b1aa38b8e2e8b1899ac292d57f05d7b352a3a181cf`.
- `conan create` returned 0. Package contains `libshairplay.so`, `dnssd.h`, `raop.h` and license.
- Upstream `make check -j1` returned 0. Registered test cases: 0/0, not a substantive test pass. See `upstream-test-inventory.txt`.
- Added installed-package consumer: 1/1 PASS. It linked against the packaged shared library and called `dnssd_init`, asserting either successful initialization or the documented missing optional-runtime error.
- Original target build log SHA-256: `39b466743707fb77e8d768a9220e5692446c5f6a93914ab41abe832070382dbd`.
- CI checkout repair validation: the same target received a fresh, hash-matched bundle in `shairplay-b64-verify-20260929T135743Z`. The text-encoded bootstrap archive decoded to the original SHA-256 `5445d896f357c7bc37bd1fb1f283470bc37273c29cbdac04234c8e4db0ac6a36`; `conan create`, upstream `make check -j1`, package creation, and the installed-package consumer all passed. New target log SHA-256: `cfee4d8c32c0fe66909129e134a3ae05765c38287d5593ba8c4b987979de82b3`.
- Previous frozen runs failed at `config.guess` platform recognition, then DNS-SD header detection and Automake regeneration. Those records remain separate failed runs and are not counted toward final PASS.
- PR #13843 CI #64900 failed while applying a GitCode diff that omitted binary patch data for the original bootstrap archive; it never reached Conan. The text-encoded repair awaits a new platform CI and AI Review.
- CI #65024 and #65080 reached `conan create`, then failed at `config.status` writing `subs1.awk` inside its restrictive temporary directory. On 2026-09-30 the OHOS-only `umask 022` fix passed a fresh target `conan create` (exit 0), upstream `make check -j1` (0 registered cases), package creation, and installed-package consumer (1/1 PASS). Raw log: `verify-ci-fix-20260930/conan-create.log`, SHA-256 `3632ba8ec41d1085cfcb6b905ca7d86d7b9053bdc0d01f7e5e433e90aa9a4bb8`. CI confirmation remains pending.
