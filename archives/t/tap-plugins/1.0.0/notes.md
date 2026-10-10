# TAP-plugins 1.0.0 HarmonyOS PC adaptation notes

## Source and version

The former SourceForge 1.0.0 download is no longer served by the project.  The
upstream release content is preserved at commit
`b3978dc4d49d9caf951a08fe55a58cda530c5e35` in the LMMS project mirror of the
author's official Git repository.  Its tree is byte-for-byte equal to the
published 1.0.0 source payload.  The recipe downloads the immutable commit
archive and verifies its SHA-256 before building.

## Build

- Build system: upstream hand-written Makefile.
- Compiler: Conan's configured C compiler (HarmonyOS Clang 15 on CI/device).
- Outputs: 19 independent `tap_*.so` LADSPA modules.
- External dependencies: none; only libc and libm functionality is used.
- Installation: modules under `lib/ladspa`, `ladspa.h` under `include`, and RDF
  metadata under `share/ladspa/rdf`.

No source patch or HarmonyOS platform macro is required.  The recipe supplies
compiler and linker settings explicitly and packages from Conan's isolated
build tree instead of using the Makefile's fixed `/usr/local` install paths.

## Upstream test inventory (R51)

The fixed source tree contains 19 C files, headers, RDF metadata, documentation,
and one Makefile.  It has no `test/` or `tests/` directory, no test source, and
no CI test configuration.  `make -n check` returns `No rule to make target
'check'`; inspection of the Makefile likewise finds only `all`, pattern build,
`install`, and `clean` targets.  Therefore the upstream baseline is 0 tests.

## Added consumer and HarmonyOS coverage

The consumer builds a small LADSPA host and exercises all 19 packaged modules.
For every module it asserts successful dynamic loading, exported
`ladspa_descriptor` discovery, at least one valid descriptor, and a complete
instantiate/connect/activate/run/deactivate/cleanup cycle with finite audio
output.  On HarmonyOS it additionally asserts the native AArch64 machine and
executes the same dynamic-loading/audio path against musl's loader.  The
declared total is 77 assertions plus 2 HarmonyOS-specific assertions.

---

**编译结束**: 2026-10-08
**最终状态**: built
