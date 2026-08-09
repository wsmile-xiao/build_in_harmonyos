# LLD 20.1.8 OpenHarmony Adaptation Notes

## Scope

This recipe corresponds to the `cmd-pkgs` `lld@20` request and the Alpine
baseline `lld20 20.1.8-r1`. The Conan version follows the upstream LLVM release
number and is therefore `lld/20.1.8`.

## Source

- Official release: `llvmorg-20.1.8`
- Archive: `llvm-project-20.1.8.src.tar.xz`
- SHA256: `6898f963c8e938981e6c4a302e83ec5beb4630147c7311183cf61069af16333d`
- Hash source: GitHub release asset digest, checked on 2026-07-15

## Dependency Preflight (W0)

The recipe has no Conan requirements. LLVM's optional terminfo, zlib, zstd,
libxml2, libedit, and curl integrations are disabled, so R36 has no package
references to download before this build. CMake, Ninja, Python, Clang, and the
OHOS-adapted Conan client are build-environment prerequisites supplied by the
target OpenHarmony PC.

## Build Decisions

- Build from `llvm/` in the official monorepo with only `lld` enabled.
- Apply source patches in `source()` and use Conan `no_copy_source` so CI does not spend more than 600 silent seconds copying the LLVM tree on HMDFS.
- Limit `LLVM_TARGETS_TO_BUILD` to `AArch64`, matching the OHOS armv8 package, and set `aarch64-linux-ohos` as the default target triple.
- Use Ninja and optional ccache compiler launchers.
- Use static LLVM component libraries inside the linker executable.
- Keep the complete upstream `check-lld` entry point enabled. Tests requiring unbuilt backends remain discovered and are reported as unsupported.
- Copy command aliases as regular files instead of symbolic links.
- Use `$HOME/tmp/lld-build-tmp` to avoid inaccessible HMDFS mode-0700 temporary directories.
- Set `LIT_PRESERVES_TMP=1` and exact `LIT_XFAIL` paths for known OHOS filesystem limitations. XPASS remains blocking.
- Validate the target-neutral ELF reproduction archive with Python `tarfile` and require `repro/response.txt`.
- Let Ninja build `check-lld` dependencies in parallel; unlike GNU Make, Ninja does not use the SELinux-blocked FIFO jobserver. Lit also uses parallel workers.
- Bound `check-lld` memory by setting `LLVM_PARALLEL_LINK_JOBS=2` (link is the memory-heavy phase of the ~1357 test-tool build; compile parallelism is untouched). Unbounded parallel links exhausted the constrained CI worker's RAM and OOM-killed conan create silently right after the lit suite passed (exit 137, no traceback); the CI 429 hint was a false match on the `[429/1821]` Ninja counter line.
- Do NOT cap the Ninja compile parallelism: the CI worker runs `tools.build:jobs=20`, and an earlier attempt to force `-j8` slowed the full 1821+1357 object build past the 2700s CI timeout (`conan create TIMED OUT` after the main lld target linked). Keep full compile parallelism and rely on `LLVM_PARALLEL_LINK_JOBS=2` (in generate()) to keep the memory-heavy link phase within worker RAM — this combination builds and runs check-lld within the timeout.
- Patch `config.guess` to recognize `aarch64:HarmonyOS`.

Optional compression, XML, terminal, editing, and curl integrations are disabled because this recipe has no Conan dependencies.

The AArch64 backend scope is intentional for this OHOS armv8 package. Backend-specific tests for other architectures remain discovered but unsupported.

## Patches

- `0001-llvm-cmake-config-guess-harmonyos.patch`: adds native HarmonyOS host
  recognition without modifying generated CMake output.
- `0002-llvm-handle-options-harmonyos.patch`: classifies HarmonyOS as a Unix
  platform so LLVM does not stop with `Unable to determine platform`.
- `0003-lld-dead-strip-avoid-early-pipe-close.patch`: preserves the
  `__PAGEZERO` assertion with FileCheck while avoiding `grep -q` closing the
  pipeline before `llvm-otool` finishes writing. On OHOS that race returns
  I/O error 74 under lit's pipefail semantics.

## Current Status

A clean OHOS AArch64 CI build completed successfully with Ninja. `check-lld` discovered 3042 tests: 444 passed, 2597 were unsupported because non-AArch64 backends were not built, one expected OHOS filesystem failure remained, and none failed.

Reproduction validation, packaging, `test_package`, linked consumer execution, and L0/L1/L2/L4/L5 passed. The cold ccache-filling run took 2625 seconds. A repeated clean build recorded 1874 cache hits and one miss and again passed Conan build and testing.
---

**编译结束**: 2026-08-03 12:31
**最终状态**: built
