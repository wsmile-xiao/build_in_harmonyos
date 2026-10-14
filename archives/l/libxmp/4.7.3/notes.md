# libxmp 4.7.3 native adaptation notes

## Current complete-tag successor (supersedes incomplete-scope notes below)

The official full archive completed with curl RC0: 20858915 bytes, SHA256 f2ee83c3ec146d5024bcba2a094ba9cf48eebbf9518bca02cf2e7cb139889a43. Every one of the 3277 files matched the exact Git-tag blob inventory. Recipe now uses this immutable official source URL, enables the unchanged complete CMake suite, and rejects a missing development test inventory.

Native r5 on the current boot passed 1013/1013 development cases, the release test program, and the 131-assertion API consumer against the native build. Two CTest programs passed. Final source/log audit counts three release rendering cases (test.it, test.itz, test.xm), giving 1016 logical upstream cases; the preliminary mixed program/case count 1014 is superseded. All 12 receipts and release/postrelease passed; log SHA256 93c0d1d05074d7f5674b5cb00cc898b7a7d9ecd515e3e32d3c7f4b20b373259f. No upstream exclusions or expected-output edits. The r4 redundant Make entry failed on unavailable ar and remains FAIL.

Formal libxmp-finish-20261011-r1 W3 Conan create also passed all 1016 logical cases and the installed consumer; unmodified W3 log SHA256 85ae574b3461e95b2b4d176d6a2d7e94633e7af90c3d0164b87aa36096fa9c64, integrity 86510283ef090228. Aggregate finish RC1/step3,step5b,step8 remains unchanged. Legacy G1 incorrectly requires singular export_sources and a patch call for a patchless recipe; valid exports_sources actually exported the helper and Conan built, installed and consumed the library. See the preserved FAIL report. Do not claim generic conan-verify or entire finish PASS; candidate-specific knowledge and Pre-PR gates are separate. Not competition-worker CI or published.

## Historical release-only verification

The formal native release recipe now passes Conan create and installed consumer. Keep all release features (depackers and ProWizard included), shared library default; no external runtime dependencies.

For the actual OHOS/HarmonyOS CMake system, provide the missing ELF SONAME flags without falsifying system identity. Skip install-time RPATH rewriting so signed ELF bytes remain executable. Upstream CTest uses a task-scoped LD_LIBRARY_PATH to the build library; the installed consumer uses Conan VirtualRunEnv.

Final release run libxmp-conan-20261011T0730Z: release CTest 1/1; substantive consumer 131 assertions, in-memory MOD decode to 141120 nonzero PCM bytes written to a real TMPDIR file, plus HarmonyOS identity. All 12 receipts/release/postrelease PASS.
Candidate SHA256 1530335ddef5e324dd30f34d4e6644f78ed0df5deb2cd151bf693e90bd6ef359.
Log SHA256 09946cc538957fecfbb593c1fcacd7bb3d982c09fe57b718169a09c9df522b4a.

Full upstream scope is NOT complete: the release archive lacks the Git-tag test-dev tree (1013 cases). Official full-tag archives timed out three times; the third received only 9560667 bytes in 360 seconds. An alternative shallow clone was interrupted while still incomplete; its partial pack is retained but not accepted as a source. No partial tar or Git pack was used in builds. Exact upstream commit is 1e0812137e4f9e15cc026c0c75af82d71d3cb5ad.

Before submission obtain and validate the complete official Git input, execute all development tests, complete framework finish, knowledge pair/dedup and Pre-PR contracts. This is not a publication or worker CI result. No Issue/PR or remote trigger this round.
