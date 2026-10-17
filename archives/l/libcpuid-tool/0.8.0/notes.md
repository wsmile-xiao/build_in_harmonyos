# libcpuid-tool 0.8.0 adaptation notes

## Source selection

Upstream tag `0.8.0` of <https://github.com/anrieff/libcpuid> (official
GitHub release archive). SHA256 of the tarball is recorded in
`conandata.yml`. The sibling archive `archives/l/libcpuid/0.8.0` ships the
library; this package ships the `cpuid_tool` command-line utility from the
same source tree and is intentionally independent of it (the internal
`cpuid` library is linked statically).

## W0b historical verification (mandatory, libcpuid 0.8.0 archive)

The historical `archives/l/libcpuid/0.8.0` notes/manifest/README were read
before this adaptation. Environment-transferability check: the historical
success was produced with a native device toolchain (clang 15.0.4, cmake);
the same cmake + clang toolchain exists in CI, so the semantics transfer.
The historical conclusions and how this recipe follows them:

| Historical conclusion | This adaptation |
| --- | --- |
| `-DCMAKE_SYSTEM_NAME=Linux` is mandatory (getauxval check, `UNIX` → `_GNU_SOURCE`, versioned `.so`) | Enforced in `generate()` via `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64` (R32-compliant `os in ("Linux","OHOS")` guard; knowledge E092) |
| 3 functional patches required (raw-data zeroing, ARM core counts, ARM clock) | Carried over verbatim (content-identical, header-normalized to `a/`/`b/` `strip: 1` format); re-verified to apply with conan's patch_ng |
| No build-system patches needed | No CMakeLists patches |
| Do not define `LIBCPUID_DISABLE_DEPRECATED` | `LIBCPUID_BUILD_DEPRECATED` left at default `ON` |
| ARM limits (brand/codename `unknown`, cache `-1`/`0`, `cpuid_error()` non-NULL) | Documented in README as upstream limits |

## Build and dependencies

No external dependencies (W0: `libcpuid-tool/0.8.0` absent from the ohpcd
remote — no version conflict; `requires`/`tool_requires` empty, verified by
PF4/R36 gates). Threads are only searched on DragonFly/NetBSD. Options set
in the recipe:

- `BUILD_SHARED_LIBS=OFF` — self-contained static tool binary; this package
  does not ship or conflict with the published shared `libcpuid` package.
- `LIBCPUID_BUILD_DRIVERS=OFF` — the DKMS branch installs driver sources
  into the absolute `/usr/src` prefix (not writable/wanted on OHOS).
- `LIBCPUID_ENABLE_DOCS=OFF` — deterministic build without Doxygen.

## Upstream test inventory and execution (R51 three-step method)

1. Inventory: upstream `tests/` contains a replay suite (`run_tests.py`)
   with 489 `*.test` / `*.test.xz` files across the amd, arm (armv7a/armv8a/
   armv9a), hygon, intel, via, zhaoxin vendor trees; each file holds raw CPU
   dumps plus expected `cpuid_tool --outfile` records (multiple CPU sections
   per file allowed). CMake registers `test-fast`/`test-old` custom targets
   wrapping the same suite.
2. Execution: the suite replays dumps via `cpuid_tool --load=<file>` and is
   therefore host-CPU independent. It was run on the OHOS aarch64 device
   against the native build produced with the recipe's exact cmake flags
   (clang 15, `CMAKE_SYSTEM_NAME=Linux`, static, drivers/docs off), with the
   three patches applied.
   - Result: **489/489 test files OK, 0 failed** (exit 0).
   - Evidence: `logs/upstream-suite-run.log` (task-data copy of the device
     run log; 491 lines).
   - Runner deviation (documented per R51): the device python 3.12.9 has a
     broken `os.popen` (`TypeError: can't concat str to bytes` in
     `codecs.decode` on every call, including `os.popen("echo hi")`), while
     `subprocess.run` works. `run_tests.py` reads tool output through
     `os.popen`/`os.system`, so the suite cannot run unmodified on this
     device. The comparisons were driven by
     `task-data/libcpuid-tool-0.8.0/run_upstream_tests.py`, a
     subprocess-only driver that replicates run_tests.py semantics exactly:
     same field lists (`fields_x86`/`fields_arm`), same file parsing
     (delimiter sections, `num_cpu_type`), same positional line comparison.
     No test data or expectations were modified.
3. Consumer test: `test_package/` runs the packaged binary itself on the
   target machine via `test.sh` (bash wrapper — OHOS `/system/bin/sh` is
   mksh, which may not execute ELF binaries): `cpuid_tool --version` must
   print `0.8.0`, and `cpuid_tool --report` must produce a non-empty CPU
   report. Upstream test declarations live in
   `test_package/MANIFEST.yml` (required by CI gate L0e).

## Package shape

- `package_type = "application"`; only `bin/cpuid_tool` is kept (upstream's
  catch-all install also emits the static library, headers and pkg-config
  file; they are removed from the package).
- `commands.json` declared at software level (R38): `cpuid_tool`.
---

**编译结束**: 2026-09-20 02:56
**最终状态**: built
