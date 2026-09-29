# MAdLib 1.3.0 path reassessment

Date: 2026-09-29. Current candidate: path A+B / `【知识库扩展】`. Evidence: source archive SHA-256 `266c8818b217599ef4a039ddfdccc6a04ee5f327855979d17320c8f152a4b4ad`, final target Conan log SHA-256 `4ca43c65ba0422dbacef04b2f5bc92d864fe7ea0234013ab50efa126a761abe1`, frozen W3 validator chain head `c6a25d379172dbf58bfddf8e61d614f1103849630c52b7eb4134940afab84fa7`.

- `HD1_PRIVATE_OS_INTERFACES`: matched=false. The three source repairs touch public Autotools tuple/temporary-directory behavior and POSIX `<unistd.h>`; the consumer calls MAdLib's public API. No private HarmonyOS interface is used.
- `HD2_PRIVATE_TOOLCHAIN`: matched=false. Standard published OHOS Clang 15, Conan, Autotools, and LAPACK were sufficient; no private compiler or SDK fork was needed.
- `HD3_COMPLEX_ARCHITECTURE`: matched=false. This is one static C++ mesh library with one published numerical dependency. The three narrow patches do not introduce a new architecture or multi-process platform subsystem.
- `HD4_LARGE_DEPENDENCY_TEST_COST`: matched=false. LAPACK was already published; the release registers zero upstream Automake cases, and one installed-package consumer passed. Build retries arose from ordinary source/configuration faults, not a large unavailable dependency or test chain.

Reassess before Issue creation, `PRE_CREATE`, each push, and submission. Patch count and number of attempts are not themselves path-C evidence.
