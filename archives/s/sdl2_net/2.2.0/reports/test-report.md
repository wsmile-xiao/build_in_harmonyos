# SDL2_net 2.2.0 Test Report

## Formal Target Result

| Scope | Independent total | Passed | Not run | Status |
|---|---:|---:|---:|---|
| Upstream installed CMake consumer | 1 | 1 | 0 | pass |
| Adapted test_package consumers | 6 | 6 | 0 | pass |

The denominator counts independent executable flows. Internal assertions and
the repeated shared/static package modes do not increase either total.

## Upstream Inventory

The release has no root CTest registration. `cmake/test/main.c` is the single
installed-package consumer source. Its shared and static targets use identical
source and input and therefore represent one test entry.

The upstream consumer does not return failure when `SDLNet_Init()` fails. The
test package therefore retains a byte-identical copy as
`test_upstream_cmake_consumer.c` and runs it as its own process. The separate
adapted `test_init_version_byteorder` executable provides strict initialization
failure semantics; it does not replace or alter the upstream entry.

`showinterfaces`, `chat`, and `chatd` are sample/demo programs, not automated
tests, and are excluded from the denominator.

## Target Execution Contract

The r27 run executed the same seven test_package executables in both shared
and static fresh Conan homes. Every terminal result was success. Any
failure, timeout, unresolved result, missing executable, or package-location
mismatch requires a fix and a complete rerun.

Before native OHOS execution, the shared package library and each test
executable must be atomically re-signed and read back with exactly one
nonempty `.codesign` section. Cross-build compile-only output cannot satisfy
this runtime gate.

The TCP and UDP tests used only `127.0.0.1`; no external endpoint was involved.

## Target Fresh Evidence

The r27 runner imported the exact shared/static SDL2 r30 package trees into
fresh per-mode Conan homes, built SDL2_net, signed every generated ELF, and
executed 7/7 consumers in each mode. Logical accounting remains 1 upstream
plus 6 adapted entries, not 14.

```text
UPSTREAM_INDEPENDENT=1/1
ADAPTED_INDEPENDENT=6/6
SHARED_EXECUTION=7/7
STATIC_EXECUTION=7/7
UNEXPECTED_FAILURES=0
candidate manifest SHA256=99b8fcac1c7006fcdc7b5fc831b3a2fb36b7c0f6dc82f0ad8f15557b69ebd78b
evidence manifest SHA256=7c00d97af51a2c56e1fe8b10d9bf78391eac8c684843855b358e9610a08d3122
evidence archive SHA256=5e1f8a705e4b735feafccfdf9c1a3101b97d63c7d9ff95f8d00bc8d0b8058210
validator SHA256=167b8f27070446e69580563d140ae27e51e6aa6016593fa004eadc15f9d0b800
```

The independent validator accepted the exact 171-file evidence closure and
rechecked candidate identity, raw terminals, package hashes, dependency
integrity, AArch64 headers, `.codesign` bytes, SONAME/NEEDED entries, and
static archive membership. The published-artifact W0 gate remains separate.

`test_package/MANIFEST.yml` is one of the frozen r27 candidate inputs. Its
`execution.status: not_run` records the still-blocked published-artifact
release-chain run; it is intentionally not rewritten after r27 because that
would break the candidate manifest binding. The completed r27 execution
result is recorded in this report, the version manifest, notes, and README.

## Local Offline Validation

- Conan 2.29.1 loaded and exported both recipes without remote access. Shared
  r35 and static r36 were rebuilt from source against the same frozen local
  SDL2 candidate: HEAD `d7db0575394853b3726eda4b8e1fbbebdfc05f5b`,
  tree `21a62e26f745ebdb94bde567be94b6484d8523bb`, recipe SHA256
  `ffcf9fe68b3bc283df3bd3fb548216ab6576d3cfd86ab2b1a771d9274338a41a`.
  This is not a published artifact and does not satisfy W0 or formal W3.
- The current recipe propagates SDL2 headers, libraries, and the `shared`
  option transitively. r35 and r36 each compiled and linked the same seven
  AArch64 consumers. Shared log/binding/complete SHA256 values are
  `607812e781ff0677d1db810ed0d2956680d4545baf2b455bfda17c00902a0b56`,
  `7cc485ab80e7025b21a4ed1d2e5b63651b78c492f8697e2331e31b504189c903`,
  and `ff414b2e13b03dbd4fe353f8bba65f38aafcd42d2dfcb6573ebc59f56add8df9`.
  Static log/binding/complete SHA256 values are
  `81a87c9390b843bb2051e7af52f771a618f2d525fe65cf6fb7390d2d4aaa01cd`,
  `37cf1cb21577494dc152ba5ea291e81b6d36f408794c976492b8a97a44648d1f`,
  and `5fad7aaa8b066c7f98702f52bfd76dd2fe6aa4f0fdb6c86401d888f83fbf6b6a`.
  Both exit records are zero and target execution is `NOT_RUN`.
- The official upstream source and its vendored copy have identical SHA256
  `7153ce5a58bef3facfe26a440fc8db074a9699c8a07a12f45a49061788231556`.
- Test source files, the Conan executable tuple, CMake targets, and
  `MANIFEST.yml` map one-to-one for all seven executable entries.
- The final Windows static host r15 run started once from a nonexistent output
  root, verified and freshly extracted both official archives, then linked
  and ran 1/1 upstream and 6/6 adapted processes. TCP and UDP used only
  `127.0.0.1`. Atomic `complete` SHA256:
  `3669198e06cc2e6694c718baba2bb7e98eed7abe140797646c28dc350141b82f`;
  terminal SHA256:
  `c3cd666e6cf23c7242e716546c9acb1befc8621536fbc439a85bb4058ac728d1`;
  nested evidence-manifest SHA256:
  `d930e35f8abd16ac4f3a099e890c15f6936ce58790866a7c928d85148b35d2d2`.
- SDK 12 compiled 4/4 library sources with `-Werror` in both modes and linked
  7/7 shared plus 7/7 static AArch64 consumers. Shared SONAME/NEEDED and
  static isolation checks passed. No target ELF was executed. Log SHA256:
  `bfd3d4c625c408fc695e27f1d4f50183ca71749bf00c5a806b30873503590fb0`.
- An unpatched SDK 12 CMake shared install reproduced the duplicate
  unversioned symlink destination failure. The OHOS-only patch then installed
  one real shared library and one static archive in separate builds.
- The patched installed CMake metadata configured and linked the same seven
  independent inputs in shared and static modes. This is 7/7 plus 7/7 linkage
  coverage, not 14 additional test cases, and no target ELF was executed.
  Summary log SHA256:
  `ab27606ceb087db5150b456487ada2c7ad4ac63900990474e1a1bf434591b688`.

The earlier host and SDK results remain supporting evidence. The r27 target
run is the evidence that changes the formal result table above.

## Test Method Reuse

The six adapted process boundaries reuse the global
`openharmony-pc-wire-protocol-test-matrix`. E207 defines the shared-library
path and basename SONAME checks; the global
`openharmony-pc-libtool-avoid-version-hmdfs` entry covers HMDFS artifact
layout; E077 defines the final ELF signing/readback gate. This candidate adds
no project knowledge draft and claims no Path B. Target execution and final
package evidence are complete; published dependency consumption remains
pending.

## Current Blockers

- Fresh consumption of `sdl2/2.30.10` as a published artifact has not
  completed; the local frozen candidate is not a substitute.
- Independent W4 has not run.
