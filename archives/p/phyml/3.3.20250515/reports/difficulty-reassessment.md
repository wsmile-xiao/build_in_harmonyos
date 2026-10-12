# PhyML 3.3.20250515 high-difficulty reassessment

Evidence: staged recipe and consumer, official snapshot source inventory, W3 `w3-phyml-20261004T074245Z` PASS, raw Conan log SHA-256 `3bea39a8f9d4d0641a2cf56215c1f95bea404768e1b1cc160e9184dc18fb27f6`. Reassess on candidate change.

- `HD1_PRIVATE_OS_INTERFACES`: matched=false; the numerical executable uses public POSIX C facilities, not private OHOS APIs.
- `HD2_PRIVATE_TOOLCHAIN`: matched=false; standard Clang/Autotools and compiler-proven target tuple, no private compiler implementation.
- `HD3_COMPLEX_ARCHITECTURE`: matched=false; one executable and bounded Autotools source cleanup, no cross-service architecture redesign.
- `HD4_LARGE_DEPENDENCY_TEST_COST`: matched=false; no external Conan runtime dependencies or registered upstream test matrix, one bounded installed-tool consumer.

Effective route A+B. Work to regenerate legacy Autotools files is not itself an HD1–HD4 criterion.
