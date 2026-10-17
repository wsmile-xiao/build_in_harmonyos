# mt32emu 2.7.1 adaptation notes

## Scope

- Downstream: DOSBox issue #1093.
- Upstream tag: `libmt32emu_2_7_1`.
- Upstream commit: `6d68fbb84b018df495fafa3e154e4ba1ffbfd0df`.
- Source SHA-256:
  `e4524d52d6799a4e32a961a2e92074f14adcb2f110a4e7a06bede77050cfdaf4`.
- Only the standalone `mt32emu/` core library is in scope. The repository-root
  Qt UI, SMF-to-WAV tool, and platform drivers are not configured.

## Dependency audit

The upstream option `libmt32emu_WITH_INTERNAL_RESAMPLER` defaults to true.
That branch compiles the bundled resampler sources and has no third-party
library dependency. The external branch first tries SOXR 0.1.2 and tries
SampleRate 0.1.8 only when SOXR is unavailable. Those backends are optional
alternatives, not simultaneous prerequisites, and this recipe keeps the
internal branch enabled.

## Build adaptation

The Conan recipe supports independent shared and static package IDs. It
copies only the core source directory into the package build folder so that
OHOS-only adjustments cannot mutate Conan's source cache or another package
configuration.

The first local CMake 4.3.3 configure rejected upstream's
`cmake_minimum_required(VERSION 2.8.12)` because compatibility below 3.5 has
been removed. Project knowledge `E187` exactly matches this failure. The
recipe sets `CMAKE_POLICY_VERSION_MINIMUM=3.5`, preserving the upstream source
while enabling the supported compatibility floor; no new knowledge draft is
needed.

Conan maps OHOS to `CMAKE_SYSTEM_NAME=HarmonyOS`; the recipe supplies a small
platform module that reuses CMake's Linux linker rules. For OHOS shared builds
only, the build-folder source copy drops `VERSION` and `SOVERSION`, avoiding a
three-name symlink chain on HMDFS while retaining an unversioned shared object
and SONAME. Other platforms retain the upstream versioned-library behavior.

The validated r10 candidate signs the installed OHOS shared library after CMake has
finished installation. The test recipe signs the fully linked consumer before
execution for both shared and static package variants. Both paths write a
clean ELF, write a separate signed ELF, replace the final path, and then set
mode `0755`. Missing inputs or signing tools fail the recipe instead of
skipping target execution.

## Test accounting

- Upstream registered tests: **0**. Six core CMake files were scanned for
  `enable_testing`, `include(CTest)`, `BUILD_TESTING`, and `add_test`; all four
  registration counts were zero.
- Consumer test flows declared: **1**. The one executable locates the installed
  `MT32Emu::mt32emu` target and exercises the public C ABI version and supported
  inventory queries, context allocation and release, renderer selection, and
  the explicit `MT32EMU_RC_MISSING_ROMS` boundary.
- Multiple checks inside that executable are not counted as separate tests.
- Repeating the same flow for shared/static package variants does not increase
  the logical test count.

For OHOS, the test recipe disables CMake RPATH generation and executes through
Conan's generated runtime environment. Fresh W3 must verify that the shared
consumer contains no package-cache `RPATH` or `RUNPATH` entry. It must also
require exactly one non-empty signing section in the shared library and in
each consumer. These shared/static executions are evidence for the same one
logical consumer flow and are not counted as separate tests.

Full synthesis requires compatible control and PCM ROM images supplied by the
user. No ROM fixture is bundled or assumed, and no audio-rendering result is
claimed.

The reusable distinction between full asset-backed execution and substantive
pre-asset lifecycle coverage was not present in the local project knowledge.
This software change therefore carries paired draft `E252-draft-MT32` under
`knowledge/graph/draft/` and does not modify the formal graph, documentation,
index, or `SUMMARY.md`.

## Current state

Fresh Conan W3 r10 passed on the known OHOS arm64 device. The one logical
consumer flow passed once for the shared package and once for the static
package; these are packaging repetitions and the reported count remains
`1/1`. The upstream registered count remains `0`. The shared library and both
consumers had one non-empty signing section, and the shared consumer had no
RPATH or RUNPATH. The candidate-manifest SHA-256 is
`4166bff68123a779082555ee4193090fa8b9d54443442f024bd918a5d2b7ba52` and
the runner SHA-256 is
`07a86cde89765c1df9035c560e1c60c4e2bdb80813639b94f995bba07749c8e4`.
The returned evidence passed the strict hash-closure validator.
