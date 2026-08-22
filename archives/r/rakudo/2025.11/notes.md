# Rakudo 2025.11 HarmonyOS PC adaptation notes

## Upstream

- Repository: https://github.com/rakudo/rakudo
- Release source: `rakudo-2025.11.tar.gz`
- Release SHA256: `9f58f4ca075d740058a49a295e862a079dcdecb3b74c01f0717bb46135a7673c`
- Required NQP revision: `2025.11`

The official release archive includes the pinned `nqp-configure` submodule. It is preferred over GitHub's generated tag archive, which omits submodule contents.

## Build and tests

Rakudo is configured for the MoarVM backend with a relocatable staging prefix containing the packaged MoarVM and NQP runtime. Because NQP's exported `--show-config` records its Conan build-cache prefix, the recipe uses a build-only proxy during Configure to report the merged staging paths; normal NQP execution is passed through unchanged, and the real executable is restored immediately afterward. MoarVM include and library flags are also supplied to every make phase. HMDFS does not allow direct core-repository installation into the copied dependency tree, so `make install` uses a writable DESTDIR under `TMPDIR` and the installed tree is copied back into staging; package permissions are normalized to 755 for directories/executables and 644 for regular data files before publication. The test environment copies the installed staging `rakudo-m` into a temporary test tree `bin/` and keeps the `share/` layout adjacent to it, so `harness5` child processes use the installed runtime rather than the build runner's empty `gen/build_rakudo_home`. It exposes the staging core repository as `RAKULIB=inst#<stage>/share/perl6/core`, and copies the published MoarVM `moar` executable into the temporary test tree, placing that tree and the dependency `bin` directory first in `PATH` for reproducible-build tests. The upstream harness still forces `RAKULIB=./lib`; the temporary installed runner preserves the correct runtime home for NativeCall and reproducible-build tests. The complete `make test` core suite passed against the published dependencies: 166 files and 2,757 tests. The separately fetched Roast specification suite is not part of `make test`. No upstream tests are modified.

The consumer test executes packaged `raku` and validates the required JIT-disabled environment, exact application package scope, version reporting, collections, hashes, UTF-8 encoding and decoding, object construction and methods (12 assertions).

The package keeps the MoarVM and NQP runtime closure required by `raku`, while removing development headers, pkg-config metadata and debug/profiler helper launchers. Both direct runtime dependencies are declared explicitly.

## Dependency status

Both exact runtime dependencies, `moarvm/2025.11` and `nqp/2025.11`, are published in the `ohpcd` Conan Remote. W0/R36 is satisfied and Rakudo can proceed through formal CI and publication.
---

**编译结束**: 2026-08-19 02:50
**最终状态**: built
