# Probe 02.21 adaptation notes

## Provenance and licensing

Source: official rlabduke/probe tag `02.21`, commit `c8750aa34139c5aa861a581a53d7f61804c03faf`; archive SHA256 `f9d5f2ce7e9c8650321cef24716618b0537077919701aab5c14f75076b294e22`.

This tag has no LICENSE.txt. Probe source/header notices permit redistribution/modification subject to preserving the notice and making modified versions available for free; they also disclaim warranty. `probe.c` carries J. Michael Word's 1996–2013 copyright, while other source/header notices carry 1999. `hybrid_36_c.c` has its own unrestricted Open Source statement attributed to Ralf W. Grosse-Kunstleve (February 2007); its header provides declarations only. Recipe packaging extracts each matching comment block verbatim, labels it by original filename, and includes both notice families. Local LicenseRef names describe these notices and are not claims of an SPDX-approved standard license. No current-master license is copied.

## Upstream test census

The complete extracted file inventory was inspected. CMake compiles 12 C files: `abin.c`, `atomprops.c`, `autobondrot.c`, `dots.c`, `geom3d.c`, `hybrid_36_c.c`, `readPDBrecs.c`, `parse.c`, `select.c`, `stdconntable.c`, `utility.c`, `probe.c`. Headers, `.gitignore`, and these build/documentation files account for the rest of the tree:

- `CMakeLists.txt`: only executable target `probe` and system `m` linkage; no `enable_testing`, `add_test`, CTest include, or install rules.
- `Makefile`, `Makefile.linux`, `Makefile.macOSX`, `Makefile.sgi`, `Makefile.sgiDebug`, `Makefile.sgiold`, `Makefile.sun`: compile/clean/install targets; `installtest` moves the executable to `/local/bin/probeTest` and is not a test.
- `Makefile.dcrHack`, `Makefile.winxp-cygwin`: compile/clean targets, no test/check target.
- `SConscript`: executable build only. `libtbx_refresh.py`: integration-time checksum warning for an external iotbx source file, no test suite. `buildep`: dependency generation only. `command_line/probe.launch`: libtbx executable dispatch declarations.
- `README.probe.txt` and `README.autobondrot.txt`: usage examples and input descriptions, no bundled PDB fixture or automated tests.

No `test/` or `tests/` directories, standalone test files, embedded hybrid36 test harness, or registered tests were found. Upstream suite count is zero, so no upstream pass percentage is reported and `cmake.test()` is not called. All eleven consumer test methods are supplemental and explicitly identified as such; the baseline before the two alias tests had nine.

## Recipe and consumer design

Native integration attempt 1 failed during source extraction with `BadZipFile`, after a successful source checksum check. This matches knowledge entry E276: the codeload URL basename is `02.21`, and Conan chooses its decompressor by downloaded filename suffix. `source()` now explicitly passes `filename="probe-02.21.tar.gz"`; official URL, SHA256 and `strip_root=True` are unchanged. An offline check exercises the recipe through real Conan `get()` and `unzip()` with mocked download/tar extraction/cleanup, verifying tar.gz dispatch and unchanged provenance. It failed before the fix and passed afterward. The controller then reported a successful native baseline create and all nine tests passing. This extraction fix itself needs no source patch.

The recipe uses upstream CMake unchanged, delegates toolchain selection to Conan, and copies the generated executable from the CMake build binary directory because no install rules exist. It fails packaging when that executable is missing. There are no third-party requirements. `export_sources()` exports the single CLI alias patch declared in conandata, and `build()` applies it before configuring CMake.

The native Python driver receives the absolute installed `bin/probe` and absolute compiled helper paths. Both must exist; no PATH fallback is permitted. Each child process has a 30-second timeout. The test recipe raises an explicit error when `can_run` is false. A caller intentionally performing a build-only cross check can use Conan's explicit `--test-folder=` option; that is not a test pass.

The synthetic four-atom PDB fixture has two chains. Tests assert nonzero SELF contacts/area, ONCE source/target identities and finite numeric fields, equivalence of BOTH to both ONCE directions, actual OUT coordinates, empty selection, missing-file failure and unknown-record behavior. They do not impose an architecture-dependent golden floating-point dot count. Upstream silently accepts some malformed numeric fields; the malformed-input case specifically tests an unrecognized PDB record and the documented observed no-atoms diagnostic, not universal malformed-input rejection.

`platform_probe.c` requires the compiler's genuine `__OHOS__` macro when Conan targets OHOS. Its OHOS branch checks `uname.sysname == HarmonyOS` and the runtime machine against the compiled architecture. It exercises C-locale decimal parsing, fixed-width formatting, libm distance calculation, and ERANGE/infinity overflow handling. The same native suite also runs the actual packaged Probe CLI. This is a HarmonyOS PC test contract; another kernel reporting `Linux` would require separate validation rather than weakening the PC assertion.

## Verification and environment separation

Historical handoff status: the current alias-patched revision was **pending native verification** at the time of the initial implementation handoff. The baseline passed nine native tests, but that result did not certify the subsequent patch. The final native verification below supersedes this interim status; the package is built locally and not published.

- Earlier Windows MinGW exploration of unmodified upstream source produced version `probe.2.21.211221`, SELF total 126, nonzero BOTH directions, ONCE raw records and OUT points. Missing input exited 1; unrecognized records exited 0 with `No atom data in input.` These observations guided assertions and are not a Conan package test result.
- Earlier controller x86_64 SDK/emulator exploration used its own environment; no ARM64 runtime success is inferred from it.
- Current controller-provided native device: `OpenHarmony-6.1.0.115`, `uname` reports `HarmonyOS`, `aarch64`, HongMeng Kernel 1.12.0. Python 3.12.9, Conan 2.29.1, Clang 15.0.4 (`aarch64-unknown-linux-ohos`), CMake 4.1.2, Ninja 1.13.1. This is distinct from the older 6.0 x86_64 emulator.
- At the initial implementation handoff, the controller had evidence for the baseline native package creation and all nine consumer cases: recipe revision `59a15f0c522f4ad6fe5d72fcade1528e`, package ID `6b129b068851896169fae42d399fa922d239ce8a`, package revision `73c8871e954559ded397d2f5432b46c3`. The subsequent eleven-case creation, CI gates and independent review are recorded in the final verification section below.

The original plan's optional HDC transport was superseded by the user's native SSH device instruction. No HDC runner is included. Native Python is supplied by the device environment, not installed by the recipe.

## Native CI long-option compatibility

The controller confirmed that the original native executable rejects both `--version` and `--help` with exit 1, while `-version` succeeds. Generic Conan verification L2 requires the double-dash forms. The requested change is limited to exact aliases for these two options; every original flag/parser rule and all numerical code must remain unchanged.

Two consumer methods have been added, taking the current suite to 11 cases and 39 static Python assertion call sites. They require the real version string, help syntax/SELF documentation, equality with original option output, and continued rejection of unsupported double-dash forms. Python syntax and declared census passed at handoff; the later native runtime result is recorded in the final verification section below.

`patches/0001-probe.c.patch` was generated by the unmodified repository `track-edit add` and `refresh-patch --auto` commands in local Ubuntu WSL, using `--project-dir .ohc/king-probe-02.21/patch-context`. The actual source edit adds exact `strcmp` alternatives to the two existing HELP/VERSION branches: two lines added/two removed, no broader argument normalization or numerical changes. It is portable CLI compatibility, so no OHOS-only guard is appropriate. The tool's per-file statistics display `0 files` because they count optional `diff` headers; the generated unified patch actually changes one file, `probe.c`.

Task-local preparation rechecked the original tarball SHA, freshly extracted a distinct original tree, verified all original source files equal the working tree before edits, and invoked the repository's real snapshot/context functions. A scratch-only directory mapping directs output solely to this archive version. No root context, global configuration, `init-build`, branch synchronization, handmade patch, or fabricated success record was used. Later permission to create a root context was unnecessary because this solution was already working.

The generator's real `patch --dry-run -p1` passed. A separate offline Conan API check exported and applied the generated patch to a fresh original-source copy, confirmed the result exactly equals tracked `probe.c` before the mocked configure boundary, and confirmed every other original file is unchanged. No compiler or executable was run by Task 1. Generated source hash metadata is retained in the version manifest. Native patched build/execution remains a separate required check.

Controller reports all 12 original infrastructure regression suites passed using an explicit task-local Git exact-working-directory adapter. The test files/assertions were unchanged, but this is **not** an unmodified direct invocation of the suite. The earlier separation from archive/native Conan integration was a handoff-time limitation; the final archive integration result is recorded below.

Controller also identified an existing G4 Conan cache JSON lookup using the wrong key path, which can silently skip artifact checks. No infrastructure edit is included. The controller will independently resolve the actual package path and check artifacts plus L2/L4; a skipped G4 path must not be reported as verified artifacts.

Static preflight: controller reports all checks except PF9 passed. PF9 misclassifies required software-level `README.md`, `manifest.yaml`, and `commands.json` as missing a version layer, conflicting with R38/review-memory (lines 128–137) and the documented directory tree (line 149). Required files are retained in place; no infrastructure changes are included. The conflict remains a pre-PR readiness blocker for the controller to document. No PR was requested or created.

## Final native verification — 2026-09-19

The alias-patched package was built and tested natively on the supplied `OpenHarmony-6.1.0.115` ARM64 PC environment (`uname`: HarmonyOS/aarch64; Conan 2.29.1; clang 15). The consumer test package ran **11/11 tests successfully**, including both exact long-option compatibility cases and the OHOS-specific runtime probe. The installed executable was passed by absolute package path; no PATH fallback was used.

The repository W3 local CI flow (`setup.sh` plus `build_and_test.sh`) passed with exit code 0. The repository Conan verifier passed G0/G1/G2/G3/L2/L4/L5 as reported by its generated report; its G4/L2/L4 cache lookup did not resolve the Conan 2 package JSON shape, so the controller independently verified the actual cache path, package contents, version execution, AArch64/HarmonyOS ELF note, NX, PIE, full RELRO, and sole `libc.so` dependency. The independent checks passed. The generated W3 result records exit code 0 and log SHA256 `65fb4ed5c4184af2f3d78356c3899f7fb619ddaf7f44560a088da931ceb78ed3`.

Final package identity: recipe revision `664316b1639b3cea33d29081bb5cfabc`, package ID `6b129b068851896169fae42d399fa922d239ce8a`, installed binary SHA256 `8fab2df154033bc3eee23f461d62ea58e92c7f65b1edab59545994368a2a4fa7`. Status is **built**, not published. The older OpenHarmony 6.0 x86_64 VM remains supplemental evidence only; it is not used for the native ARM64 claim.

The `finish built` command completed build verification and W3 but returned a nonzero closeout result because the generic legacy finalizer requested a `packaging/` tarball and `test-report.md`, flagged its pre-existing knowledge graph entries, and observed generated `SUMMARY.md` framework drift. These are recorded as repository-tool closeout issues, not hidden as package passes; no infrastructure files were changed and no PR was created.
