# buddy_alloc

buddy_alloc is a binary buddy memory allocator distributed as a single C99
header (`buddy_alloc.h`). It supports external-metadata (`buddy_init`) and
embedded-metadata (`buddy_embed`) arenas, aligned arenas, resize/reserve,
safe-free, change tracking and tree invariants — no recursion, no global
state, endian-agnostic, works on 32/64-bit platforms.

This archive entry adapts buddy_alloc 1.3.2 for OpenHarmony PC (arm64) through
a header-only Conan package: the public header is installed under `include/`
and consumers define `BUDDY_ALLOC_IMPLEMENTATION` in one translation unit.

Upstream tests (165 independent `test_*` cases in `tests.c` + the C++11
translation-unit test) compile and pass with the platform clang 15 toolchain;
the package also ships a HarmonyOS-specific validation test (`test_ohos`) and
a consumer use case (`test_consumer`).
