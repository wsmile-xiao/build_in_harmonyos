# SDL2_net 2.2.0 Offline Validation

## Scope

This report preserves the earlier local, non-network validation of the
candidate recipe and test sources. Target r27 evidence is summarized below;
this file still does not claim W0, W4, CI, or published-artifact consumption.

## Inputs

```text
Base HEAD: 8c5703f967b606bc454831e265005d440d26dce5
Source cache SHA256: 4e4a891988316271974ff4e9585ed1ef729a123d22c08bd473129179dc857feb
Dependency contract: sdl2/2.30.10
```

## Checks

Validation results are populated only after the corresponding command has
completed. The earlier offline stage did not provide a target result. The
later r27 target run completed against frozen, independently validated SDL2
r30 package trees; published-artifact consumption remains blocked.

## Target r27 Addendum

- Upstream independent entry: `1/1 PASS`.
- Adapted independent entries: `6/6 PASS`.
- Shared execution: `7/7 PASS`.
- Static execution: `7/7 PASS`.
- Unexpected failures: `0`.
- Candidate manifest SHA256:
  `99b8fcac1c7006fcdc7b5fc831b3a2fb36b7c0f6dc82f0ad8f15557b69ebd78b`.
- Evidence manifest SHA256:
  `7c00d97af51a2c56e1fe8b10d9bf78391eac8c684843855b358e9610a08d3122`.
- Evidence archive SHA256:
  `5e1f8a705e4b735feafccfdf9c1a3101b97d63c7d9ff95f8d00bc8d0b8058210`.

The independent validator accepted all 171 required evidence files and
rejected any missing, extra, duplicate, malformed, or non-PASS terminal.

| Check | Result |
|---|---|
| Conan 2.29.1 recipe inspect/export | pass for current patched recipe |
| Offline Conan graph, shared option propagation | pass for current recipe snapshots in shared and static modes |
| Python syntax | pass, 2 files |
| YAML parse | pass, 4 files |
| CMake patch replay on fresh official extraction | pass |
| Test source/manifest one-to-one mapping | pass, 1 upstream + 6 adapted entries |
| Exact upstream source preservation | pass; byte-identical SHA256 |
| Legacy Autotools patches absent | pass; replaced by one CMake portability patch |
| Source archive hash matches conandata | pass |
| Windows static host build/link/run | pass from one empty r15 root; 1/1 upstream + 6/6 adapted |
| SDK 12 SDL2_net library compile/link | pass, 4/4 sources in shared and static modes |
| SDK 12 AArch64 consumer link | pass, 7/7 shared and 7/7 static; not executed |
| Unpatched SDK 12 CMake shared install | expected failure; duplicate unversioned symlink destination |
| Patched SDK 12 CMake shared/static install | pass; one real `.so` or one `.a` |
| Installed CMake metadata consumer link | pass, 7/7 shared and 7/7 static; not executed |
| Local OHOS shared/static conan create | pass; 7/7 linked in each mode, target execution not run |
| Target r27 tests and ELF inspection | pass; 7/7 shared and 7/7 static, with 14 PASS terminals and zero unexpected failures |

## Commands and Evidence

Conan recipe loading used the OHOS-adapted Conan 2.29.1 executable from
`D:\HarmonyPC-tools\conan-ohpc-2.29.1`. The frozen local SDL2 candidate and
this SDL2_net recipe were exported from their worktrees into separate fresh
shared/static caches. This dependency source is not a published artifact:

```text
SDL2 HEAD: d7db0575394853b3726eda4b8e1fbbebdfc05f5b
SDL2 tree: 21a62e26f745ebdb94bde567be94b6484d8523bb
SDL2 recipe SHA256: ffcf9fe68b3bc283df3bd3fb548216ab6576d3cfd86ab2b1a771d9274338a41a
SDL2 current recipe revision in both cross caches: 2c8a6dffb7aa47552429f9025eb9c28a
SDL2_net current recipe revision: 0fdeb09205508dd7e41b856bd3e5950d
DEPENDENCY_SOURCE=LOCAL_FROZEN_CANDIDATE_NOT_PUBLISHED_ARTIFACT
```

The latest SDL2_net export included the current CMake patch and completed
without remote access or dependency resolution:

```text
exported patch sha256: 526e90d649cfe353d181f1477833f17953dffc71e37f42f34a59c176c4d627e2
summary log sha256: c3fe7451fec79e49221a03ff0137d58bee05de49f59b43d51081eeccbc56494a
REMOTE_ACCESS=NOT_USED
DEPENDENCY_RESOLUTION=NOT_RUN
CONAN_CREATE=NOT_RUN
```

An earlier option-only shared/static graph used `--no-remote --build=never`. It
showed `True/True` and `False/False`, respectively, for the `shared` option on
`sdl2_net/2.2.0` and `sdl2/2.30.10`. Both graph nodes had null `remote` and
`binary_remote` fields. The SDL2 dependency binaries remained `Missing`, as
expected. The result is not a package build or W0 result. It binds SDL2
revision `cb1b0f655e30beed9559b4f6560481f5` and SDL2_net revision
`c1e617d0fff287e1546f585ddab34af3`. Summary log SHA256:
`5fbedd709712e3dd2931c2fe1a30480bfcdd717fafab42239f737a3aa71f1217`.

The upstream source and vendored test-package copy have identical SHA256:

```text
7153ce5a58bef3facfe26a440fc8db074a9699c8a07a12f45a49061788231556
```

The final Windows host r15 run started once from a nonexistent output root,
verified both official archive hashes, extracted both archives into the fresh
root, and built static SDL2 and SDL2_net under one isolated prefix. The runner
used an exact seven-name allowlist and fixed per-source SHA256 values. It then
produced seven unique PASS terminals:

```text
HOST_UPSTREAM_SUMMARY=1/1
HOST_ADAPTED_SUMMARY=6/6
runner sha256: 87f3fc2b4e74ee9869e25e156950f85680c242cbfa1403c54afb04d8dcdd211b
complete sha256: 3669198e06cc2e6694c718baba2bb7e98eed7abe140797646c28dc350141b82f
terminal sha256: c3cd666e6cf23c7242e716546c9acb1befc8621536fbc439a85bb4058ac728d1
evidence manifest sha256: d930e35f8abd16ac4f3a099e890c15f6936ce58790866a7c928d85148b35d2d2
```

The atomic `complete` binds runner/source/input/toolchain/discovery/terminal,
all build/compile/run logs, and all seven executable hashes. Independent
`sha256sum -c` readback passed for every evidence and artifact entry. No
failure, timeout, skip, unknown, or error terminal was present.

The earlier incremental diagnostic run is retained only as historical
preflight evidence; it is not the final counted host result. Its log SHA256 is
`a5b065ad63f294e61e02cc10e28e8596cda01fdf86f32d71e009063ae4893482`.

The frozen SDL2 candidate was then rebuilt from source in two isolated Conan
homes. The SDL2_net package and all seven consumers were also rebuilt from
source. Both runs used `--no-remote`, recorded exit code zero, and terminated
with target execution `NOT_RUN`:

```text
shared r35 consumers: 7/7
shared log sha256: 607812e781ff0677d1db810ed0d2956680d4545baf2b455bfda17c00902a0b56
shared binding sha256: 7cc485ab80e7025b21a4ed1d2e5b63651b78c492f8697e2331e31b504189c903
shared complete sha256: ff414b2e13b03dbd4fe353f8bba65f38aafcd42d2dfcb6573ebc59f56add8df9
static r36 consumers: 7/7
static log sha256: 81a87c9390b843bb2051e7af52f771a618f2d525fe65cf6fb7390d2d4aaa01cd
static binding sha256: 37cf1cb21577494dc152ba5ea291e81b6d36f408794c976492b8a97a44648d1f
static complete sha256: 5fad7aaa8b066c7f98702f52bfd76dd2fe6aa4f0fdb6c86401d888f83fbf6b6a
TARGET_EXECUTION=NOT_RUN
FORMAL_W3=BLOCKED_UNTIL_SDL2_2_30_10_PUBLISHED
```

The read-only r35/r36 validator bound current recipe bytes, both binding files,
both logs, both exit records, both complete records, and the exact seven
consumer files in each mode. Its SHA256 is
`db8fdc5a44973595db1881167213d14e3381102c54b35d90955c0bb5db90a291`.

SDK 12 then compiled the four library sources in separate shared/static object
roots with `-Werror`, linked one unversioned shared library and one static
archive, and linked all seven consumers in both modes. Mechanical readelf
checks required AArch64, shared SONAME `libSDL2_net.so`, shared NEEDED
`libSDL2.so`, and no SDL shared NEEDED entries in static consumers:

```text
SDK12_LIBRARY_SOURCES=4/4
SDK12_SHARED_LINK_SUMMARY=7/7
SDK12_STATIC_LINK_SUMMARY=7/7
SDK12_EXECUTION=NOT_RUN
log sha256: bfd3d4c625c408fc695e27f1d4f50183ca71749bf00c5a806b30873503590fb0
shared library sha256: 8526b0fb52c9fb9a9814fa682918ceb128f238e2032258dc3fd2f94bf7224a2d
static library sha256: 9baa57d4a415c8c9b20bdc69b7e84add7b82e2bb18529bda5988afbc797c9b4b
```

An unmodified upstream SDK 12 CMake shared install first reproduced the
version-link collision. It installed the versioned library and aliases, then
failed when the extra `libSDL2_net.so` symlink targeted an existing path:

```text
unpatched install log sha256: 49903a3dd6f57c5145b3af6e0b790653552ca9698e1962052c973fb4ccc632d3
terminal: file INSTALL cannot read symlink ... File exists
```

Patch `0001-CMakeLists.txt.patch` (SHA256
`526e90d649cfe353d181f1477833f17953dffc71e37f42f34a59c176c4d627e2`)
limits the changed behavior to `OHOS|HarmonyOS`. Patched CMake shared/static
install and direct consumption of their installed CMake metadata then passed:

```text
PATCHED_SHARED_ARTIFACT=PASS
PATCHED_SHARED_SHA256=208d24232cbdd4cc93175213e760036bac0805df0dbf9ea7c874b98b27b41e4e
PATCHED_STATIC_ARTIFACT=PASS
PATCHED_STATIC_SHA256=c71151ec2ccb3b8b77569b4d3da9abd1f14fab68ec551d22b1a07c85b0d53cd4
METADATA_SHARED_CONSUMERS=7/7
METADATA_STATIC_CONSUMERS=7/7
TARGET_ELF_EXECUTION=NOT_RUN
summary log sha256: 5c61b460293018089efae6cd14103d72f5b5ce356d2357ac5b0deb3accee5897
```

Local simulated tools then exercised the root recipe and test-package signing
helpers. Both classes selected `llvm-objcopy-15` from a `clang-15` toolchain,
preserved an existing nonempty signature, preserved the original ELF when the
signer failed, and removed all temporary files:

```text
SIGNING_HELPER_CLASSES=2/2
VERSIONED_LLVM_RESOLUTION=2/2
ATOMIC_SIGN_SUCCESS=2/2
EXISTING_CODESIGN_PRESERVED=2/2
SIGN_FAILURE_PRESERVES_INPUT=2/2
TEMPORARY_CLEANUP=2/2
SIGNING_HELPERS_VALID=1
```

The current helper validator additionally rejects copying a verified signer
output into a second ELF before replacement. The package and all seven test
executables must retain the original signer output and execute from a native
target work root. Each successful consumer emits exactly one
`SDL2_NET_TEST_PASS name=<entry>` marker after its process exits zero; those
markers identify the seven independent entries without splitting assertions.

This fixture did not call the real OHOS signer and did not execute target
ELFs. Native W3 must still prove real `.codesign` contents and runtime.

The current validator was then run against six isolated candidate mutations.
The `r4` runner SHA256 is
`7aca4ba7b7c50c164d0b0acc94eb21eefc38241d960d495ae706a7b3fbbffc0b`.
Each
mutation preserved the original evidence files but changed one contract, and
all six were rejected for the intended reason:

```text
FAIL_CLOSED_PASS=upstream-copy
FAIL_CLOSED_PASS=test-manifest
FAIL_CLOSED_PASS=patch-declaration
FAIL_CLOSED_PASS=recipe-bytes
FAIL_CLOSED_PASS=formal-pass
FAIL_CLOSED_PASS=top-level-docs
FAIL_CLOSED_SUMMARY=6/6
log sha256: 5424cad81739bb798e37fe1a331d9c1c7cf01ebd0b1f42689029dc93ed7d58c6
```

The unmutated clean-base validator terminal was retained as
`offline-candidate-clean-r6.log`; its SHA256 is
`e8c3c079ec55dae77dab92d766dfb7aaee40f9fdd97d9627a20ec8a6b7a72f7d`.

The host run is not an OpenHarmony runtime result, and SDK AArch64 binaries
were not executed. Those historical stages do not alter the completed r27
result. Only the published-artifact release-chain W0/W3 remains blocked: it
requires fresh OpenHarmony shared/static Conan builds after the SDL2
publication gate is unblocked.

## Knowledge Disposition

No new knowledge draft or Path B claim is included. The offline checks reuse
E207 (path-free dependencies and SONAME), E077 (final atomic ELF signing and
readback), and the global `openharmony-pc-libtool-avoid-version-hmdfs` entry.
The independent process boundaries and loopback-only flows reuse the global
`openharmony-pc-wire-protocol-test-matrix`. Fresh W3 still has to prove the
final package metadata, signed target processes, and artifact contracts.
