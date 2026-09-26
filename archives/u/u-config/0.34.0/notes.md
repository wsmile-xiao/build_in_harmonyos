# u-config 0.34.0 adaptation notes

- Upstream documents a packager build: invoke a C compiler directly on one
  platform-layer translation unit (`main_posix.c` for POSIX-like targets),
  which `#include`s `src/u-config.c`. The bundled Makefile is explicitly
  development-only, and its `pkg-config` target embeds the *host* system's
  `pc_path` search string, which is wrong for a cross build; the recipe
  therefore calls the OHOS clang with `-Os -o pkg-config main_posix.c` and
  injects no `PKG_CONFIG_*` macros, keeping upstream's `/usr`-based
  defaults. Runtime `PKG_CONFIG_PATH` discovery (consumer tests 3-8) and
  `PKG_CONFIG_LIBDIR` override (consumer test 9) were verified on target.
- The upstream suite `main_test.c` is a libc platform layer that runs the
  entry point over an in-memory virtual filesystem: platform-independent,
  no test data. It is compiled with upstream's debugging flags including
  `-fsanitize=undefined -fsanitize-undefined-trap-on-error` (trap mode
  needs no ubsan runtime library, so it links against plain musl) plus
  `-Wno-clobbered` as the Makefile's own `tests` target does. All 63
  assertions pass natively on the OHOS target inside `build()`.
- The cross-built ELFs execute on the device without signing (verified for
  both `tests` and `pkg-config`), so no self-signing step was needed.
- No source patches were required: v0.34.0 compiles warning-clean for
  errors with `aarch64-unknown-linux-ohos-clang` 15 in one shot.
- The package installs the same binary twice: `bin/pkg-config` (the drop-in
  name is the point of the tool) and `bin/u-config` (upstream name).
- Consumer test (`test.sh`, 10 assertions) drives the installed tool the
  way a configure script does: generates `.pc` files, checks expansion,
  token order, `--validate` accept/reject, missing-package exit code,
  `--newlines`, and `PKG_CONFIG_LIBDIR` override.
- Language preflight: task declared cpp, sources are 100% C (11 files) —
  c/cpp is one compatible family, same clang toolchain, no exception.
---

**编译结束**: 2026-09-23 23:18
**最终状态**: built
