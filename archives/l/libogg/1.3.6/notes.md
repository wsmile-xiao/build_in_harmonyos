# libogg 1.3.6 adaptation notes

## Scope

This Path A candidate replaces the incomplete historical 1.3.6 placeholder.
It uses the official Xiph release archive and has no third-party Conan
dependency. The version is the libogg reference required by the local
OpusFile/DOSBox dependency audit.

## Source

- URL: `https://downloads.xiph.org/releases/ogg/libogg-1.3.6.tar.xz`
- SHA-256: `5c8253428e181840cd20d41f3ca16557a9cc04bad4a3d04cce84808677fa1061`
- Size: 439,952 bytes

The historical `config.guess` and `config.sub` patches apply only to the old
Autotools route. The selected official CMake route does not use them, so this
candidate carries no source patch.

## Test accounting

Official `CMakeLists.txt` registers exactly two independent CTest entries:
`test_bitwise` from `src/bitwise.c` and `test_framing` from `src/framing.c`.
It calls `add_test()` without enabling CTest, so a plain CTest invocation finds
zero entries. Reusing E249, the recipe executes the two built official programs
directly and requires both process results instead of accepting an empty CTest
run.
The Conan test package adds one installed-package integration flow that creates
an Ogg page, submits it to a second stream, and verifies the recovered packet.
The logical total is therefore two upstream entries plus one integration flow.
Shared and static repetitions do not increase these totals, and internal API
checks are not split into cases.

## Current boundary

The Windows host static build ran both official programs and the installed
consumer successfully. A separate shared build ran both official programs,
but the upstream Windows import library names `ogg.dll` while CMake installs
`libogg.dll`, so the installed shared consumer cannot start. This Windows-only
metadata observation does not establish an OpenHarmony failure or success.

Fresh OpenHarmony PC W3 r4 executed shared and static Conan creates from an
eight-file locked execution-input manifest. Both modes completed the two official
programs and the installed-package consumer. Repeated modes are corroboration,
so the logical result is `2/2` upstream plus `1/1` integration, not six tests.
The host evidence is not used for this target pass count.

The r4 execution bundle contains only inputs that can affect build or tests.
Result metadata such as this file, manifests, and reports is excluded and is
frozen separately for W4, so recording the result cannot change tested bytes.
The evidence contract records exact shared/static/runner exit values and an
exact file inventory with size and SHA-256 for each payload. Its validator also
rejects an extra file, a changed runner exit, and changed log bytes. Evidence
SHA-256 values are recorded in `manifest.yaml`. A new independent W4 is
required for the r4 consumer cleanup fix. CI and publication are not claimed.
