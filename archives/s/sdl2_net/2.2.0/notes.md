# SDL2_net 2.2.0 Adaptation Notes

## Current State

- Candidate state: target shared/static builds and historical executions completed
- W0: resolved by the published static `sdl2/2.30.10` package
- Target fresh evidence: complete against the frozen, validated SDL2 r30 package trees
- Current dependency contract: 7/7 AArch64 consumers link in both SDL2_net
  modes against the published static SDL2 package
- W4: P0/P1 clear; one non-blocking documentation warning was corrected
- CI: the previous HEAD failed before SDL2 publication; this fix is pending push

The historical May archive is not treated as a Conan result. Its two
Autotools platform patches have been removed from this CMake candidate.

Conan 2.29.1 loaded and exported the patched recipe in isolated local caches.
The current recipe revision used by both cross builds is
`0fdeb09205508dd7e41b856bd3e5950d`.

## Source

```text
URL: https://github.com/libsdl-org/SDL_net/releases/download/release-2.2.0/SDL2_net-2.2.0.tar.gz
SHA256: 4e4a891988316271974ff4e9585ed1ef729a123d22c08bd473129179dc857feb
```

The local cached archive has the same SHA256. The offline validation did not
fetch the URL or contact a package remote.

## Target Fresh Execution r27

The r27 runner started once from a new target root. It created separate fresh
Conan homes for shared and static modes, imported the exact SDL2 r30 package
trees without rebuilding SDL2, built SDL2_net, signed the generated shared
library and all consumers, and executed the same seven independent entries in
both modes. The repeated modes validate package variants and do not double the
logical test count.

```text
upstream independent: 1/1 PASS
adapted independent: 6/6 PASS
shared execution: 7/7 PASS
static execution: 7/7 PASS
unexpected failures: 0
candidate manifest SHA256: 99b8fcac1c7006fcdc7b5fc831b3a2fb36b7c0f6dc82f0ad8f15557b69ebd78b
evidence manifest SHA256: 7c00d97af51a2c56e1fe8b10d9bf78391eac8c684843855b358e9610a08d3122
evidence archive SHA256: 5e1f8a705e4b735feafccfdf9c1a3101b97d63c7d9ff95f8d00bc8d0b8058210
SDL2 evidence manifest SHA256: a5ad77e38c811109ae44bb7189ebde102dba50f6dbbb61484cfac459c52ae2d6
```

The independent validator bound HEAD
`acbef2a1d80f51f018f87451ca0dd335feb1cb9b`, the exact candidate manifest,
171 evidence files, all signed ELF semantics, both dependency package trees,
and 14 execution terminals. This proves the target result; it does not claim
that `sdl2/2.30.10` has been published or consumed from the release remote.

## Dependency Contract

The recipe requires exactly the published static `sdl2/2.30.10` package for
both SDL2_net modes. It binds SDL2's installed native CMake config explicitly,
because the published recipe's generated Conan target does not match the
upstream SDL2_net target contract:

| SDL2_net mode | SDL2 mode | SDL2 target | SDL2_net target |
|---|---|---|---|
| shared | static | `SDL2::SDL2` (alias to `SDL2::SDL2-static`) | `SDL2_net::SDL2_net` |
| static | static | `SDL2::SDL2-static` | `SDL2_net::SDL2_net-static` |

The SDL2_net package propagates `sdl2::sdl2` through `cpp_info.requires`.
Its Conan requirement explicitly enables transitive headers and libraries so
consumers receive SDL2's `include/SDL2` directory and selected library through
SDL2_net rather than through manually supplied paths.
A retained pre-fix local `--no-remote --build=never` graph bound SDL2 revision
`cb1b0f655e30beed9559b4f6560481f5` and SDL2_net revision
`c1e617d0fff287e1546f585ddab34af3`. That historical graph matched shared and
static options in both nodes; the current contract deliberately fixes SDL2 to
static. Remote fields are null, and dependency binaries remain missing. The
retained graph's summary log SHA256 is
`5fbedd709712e3dd2931c2fe1a30480bfcdd717fafab42239f737a3aa71f1217`.

## Build Configuration

The upstream CMake build is used with explicit options:

```text
BUILD_SHARED_LIBS=<recipe shared option>
CMAKE_POSITION_INDEPENDENT_CODE=<recipe fPIC option>
SDL2NET_INSTALL=ON
SDL2NET_SAMPLES=OFF
```

For `OHOS|HarmonyOS`, the recipe generates local `Platform` modules that
include CMake's Linux platform rules and supplies the missing C/CXX SONAME,
runtime, and rpath-link flag contracts. This is required so the scoped CMake
patch yields one real `libSDL2_net.so` with a basename SONAME when newer CMake
does not recognize HarmonyOS. Patches are applied once in `source()`, before
the shared/static build folders diverge.

On a native OHOS build, `package()` atomically re-signs the real shared
library before test-package consumers load it. Before execution, the test
package atomically re-signs each of its seven independent executables. Tool
resolution honors explicit Conan configuration, derives versioned LLVM names
from `clang-N`, then checks the HNP directory and PATH. Every result is read
back with `llvm-readelf`/`llvm-objcopy` and must contain exactly one nonempty
`.codesign` section. A cross OHOS build may compile/package; when `can_run()`
is false, the test package records `NOT_RUN` and returns without execution.

Local simulated-tool fixtures exercised both recipe classes: versioned tool
resolution, unsigned and previously signed inputs, signer failure preserving
the original ELF, and complete temporary cleanup all passed 2/2. No real OHOS
ELF was signed or executed by this fixture.

The current candidate validator also rejected 6/6 isolated mutations: the exact
upstream source copy, test manifest count, patch declaration, recipe bytes,
formal pass count, and software-level stale wording. The fail-closed terminal
runner SHA256 is
`7aca4ba7b7c50c164d0b0acc94eb21eefc38241d960d495ae706a7b3fbbffc0b`;
the `r5` terminal log SHA256 is
`5424cad81739bb798e37fe1a331d9c1c7cf01ebd0b1f42689029dc93ed7d58c6`.
The final clean-base success terminal is retained as
`offline-candidate-clean-r6.log`; its SHA256 is
`e8c3c079ec55dae77dab92d766dfb7aaee40f9fdd97d9627a20ec8a6b7a72f7d`.

Samples are disabled even when SDL2test is available, so the package contents
do not depend on ambient build tools. The upstream release contains no CTest
registration in the root build.

The recipe applies `0001-CMakeLists.txt.patch` after source extraction. Its
SHA256 is
`526e90d649cfe353d181f1477833f17953dffc71e37f42f34a59c176c4d627e2`.
Only `CMAKE_SYSTEM_NAME` values `OHOS` and `HarmonyOS` skip upstream
`VERSION`/`SOVERSION`, versioned `OUTPUT_NAME`, and the extra unversioned
symlink create/install steps. Other platforms retain the upstream branches.

## Knowledge Disposition

This candidate adds no knowledge draft and makes no Path B claim. It reuses
E207 for path-free shared dependencies and basename SONAME checks, the global
`openharmony-pc-libtool-avoid-version-hmdfs` entry for output without HMDFS
version symlinks, and E077 for post-processing followed by one atomic final
signature and readback. The six adapted consumers reuse the global
`openharmony-pc-wire-protocol-test-matrix`: independent inputs and failure
boundaries are counted once, internal assertions stay internal, and
shared/static repetitions do not increase the total.

The missing `find_dependency(SDL2)` call and the upstream consumer's
`SDLNet_Init` exit semantics are source-specific observations. Fresh W3 must
still prove package-root metadata discovery, the signed seven-process target
run, and the final shared/static artifact contracts.

## Installed Consumer Contract

The test package calls both `find_package(SDL2 CONFIG REQUIRED)` and
`find_package(SDL2_net CONFIG REQUIRED)`. This is required because the
upstream `SDL2_netConfig.cmake` includes its exported targets but does not call
`find_dependency(SDL2)`.

At configure time, the test CMake project inspects the expected imported
targets and requires include, link, or imported-location evidence under the
current Conan package folders. This prevents a host SDL2 or SDL2_net install
from satisfying the consumer accidentally.

## Independent Test Entries

The upstream release has one independent installation consumer under
`cmake/test`. Its shared and static executables use the same source and input,
so it is counted once. `test_upstream_cmake_consumer.c` is a byte-identical
copy of the official `cmake/test/main.c` and preserves its original exit
semantics. In particular, it prints an `SDLNet_Init` error but still returns
success. The separate `test_init_version_byteorder` consumer makes
initialization failure a nonzero terminal result; it does not replace or
silently strengthen the upstream entry.

In addition to that one upstream entry, the test package contains six adapted
independent executables:

1. strict initialization, linked version, and byte-order conversion;
2. one-byte allocation, 65535-byte resize, and packet-vector boundaries;
3. deterministic overlong-host failure plus numeric and wildcard resolution;
4. UDP payload transfer over `127.0.0.1` only;
5. bidirectional TCP payload transfer over `127.0.0.1` only;
6. socket-set add, readiness, receive, delete, and cleanup.

Assertions inside one executable are audit evidence, not additional cases.
Running the same seven inputs for shared and static packages validates both
package modes but does not change the logical count of one upstream plus six
adapted entries.

## Offline Compile And Host Preflight

The final Windows static host r15 run started once from a nonexistent output
root. It verified the official SDL2 2.30.10 and SDL2_net 2.2.0 archive hashes,
extracted both archives into that root, built one isolated prefix, and
compiled all seven exact allowlisted sources with `-Werror`. The byte-identical
upstream source retained its original unused `argc`/`argv` and received only
`-Wno-unused-parameter`. Seven separate processes passed: 1/1 official
upstream and 6/6 adapted. TCP and UDP traffic stayed on `127.0.0.1`.

The atomic `complete` SHA256 is
`3669198e06cc2e6694c718baba2bb7e98eed7abe140797646c28dc350141b82f`.
It binds runner SHA256
`87f3fc2b4e74ee9869e25e156950f85680c242cbfa1403c54afb04d8dcdd211b`,
the seven-input manifest, seven unique PASS terminals, toolchain identity,
all build/compile/run logs, and the seven executable hashes. The nested
evidence-manifest SHA256 is
`d930e35f8abd16ac4f3a099e890c15f6936ce58790866a7c928d85148b35d2d2`;
the terminal TSV SHA256 is
`c3cd666e6cf23c7242e716546c9acb1befc8621536fbc439a85bb4058ac728d1`.

SDK 12 compile/link-only validation used target
`aarch64-linux-ohos` and the existing independent SDL2 shared/static stages.
All four SDL2_net library sources compiled with `-Werror` in both modes. One
real `libSDL2_net.so` was linked with SONAME `libSDL2_net.so` and NEEDED
`libSDL2.so`; a separate `libSDL2_net.a` was produced. Seven shared and seven
static consumer ELF files linked successfully, all were AArch64, and static
consumers had no SDL2 or SDL2_net shared NEEDED entry. No target ELF was
executed. The log SHA256 is
`bfd3d4c625c408fc695e27f1d4f50183ca71749bf00c5a806b30873503590fb0`.

These results are fresh host upstream/adapted execution evidence plus target
compile/link evidence. They are not target runtime, W0, CI, or publication
results.

## CMake Install And Metadata Preflight

A fresh SDK 12 CMake build of the unmodified upstream tree produced
`libSDL2_net-2.0.so.0.200.0` plus version links, then failed while installing
the separately generated `libSDL2_net.so` because that destination already
existed. The failing install log SHA256 is
`49903a3dd6f57c5145b3af6e0b790653552ca9698e1962052c973fb4ccc632d3`.

The patch above was replayed on a fresh extraction of the official archive.
The patched shared CMake build/install completed and installed exactly one
real `libSDL2_net.so`. It is AArch64, has SONAME `libSDL2_net.so`, needs
`libSDL2.so`, and has no RPATH/RUNPATH or versioned aliases. Its SHA256 is
`208d24232cbdd4cc93175213e760036bac0805df0dbf9ea7c874b98b27b41e4e`.
The patched static build/install produced exactly one `libSDL2_net.a` with
four objects and no `.so`; its SHA256 is
`c71151ec2ccb3b8b77569b4d3da9abd1f14fab68ec551d22b1a07c85b0d53cd4`.

The installed upstream CMake configuration and exported targets were then
consumed directly, with package-root guards, to configure and link all seven
test-package sources in shared and static modes. All 14 outputs are AArch64;
shared consumers need `libSDL2_net.so` and `libSDL2.so`, static consumers need
neither shared library, and none has RPATH/RUNPATH. Target ELFs were not
executed. The summary log SHA256 is
`5c61b460293018089efae6cd14103d72f5b5ce356d2357ac5b0deb3accee5897`.

These are SDK compile/link-only results, not formal W3. Fresh shared W3 must
still require one real `libSDL2_net.so`, matching SONAME/NEEDED, and no
unexpected RPATH. Fresh static W3 must require only `libSDL2_net.a` and no
SDL2_net shared NEEDED entry.

## Local Conan Cross Builds

The current SDL2 candidate was rebuilt from source in two isolated Conan homes
using Conan 2.29.1 and the SDK 12 OHOS profile. Both commands used
`--no-remote`; no dependency or package was downloaded from a remote. The
dependency input is explicitly a frozen local candidate, not a published
artifact:

```text
SDL2 HEAD d7db0575394853b3726eda4b8e1fbbebdfc05f5b
SDL2 tree 21a62e26f745ebdb94bde567be94b6484d8523bb
SDL2 recipe SHA256 ffcf9fe68b3bc283df3bd3fb548216ab6576d3cfd86ab2b1a771d9274338a41a
SDL2 recipe revision 2c8a6dffb7aa47552429f9025eb9c28a
SDL2_net recipe revision 0fdeb09205508dd7e41b856bd3e5950d
```

- Shared r35 built and packaged one `libSDL2_net.so`; all seven independent
  consumers compiled and linked. Log, binding, and complete SHA256 values are
  `607812e781ff0677d1db810ed0d2956680d4545baf2b455bfda17c00902a0b56`,
  `7cc485ab80e7025b21a4ed1d2e5b63651b78c492f8697e2331e31b504189c903`,
  and `ff414b2e13b03dbd4fe353f8bba65f38aafcd42d2dfcb6573ebc59f56add8df9`.
- Static r36 built and packaged one `libSDL2_net.a`; all seven independent
  consumers compiled and linked. Log, binding, and complete SHA256 values are
  `81a87c9390b843bb2051e7af52f771a618f2d525fe65cf6fb7390d2d4aaa01cd`,
  `37cf1cb21577494dc152ba5ea291e81b6d36f408794c976492b8a97a44648d1f`,
  and `5fad7aaa8b066c7f98702f52bfd76dd2fe6aa4f0fdb6c86401d888f83fbf6b6a`.

The read-only cross-evidence validator has SHA256
`db8fdc5a44973595db1881167213d14e3381102c54b35d90955c0bb5db90a291`.
It verifies current recipe bytes, each run's binding/log/exit/complete closure,
seven unique consumer files, the correct shared/static mode, and the unchanged
formal W3 blocker.

The same seven sources were used in both modes, so this is seven linkage
entries exercised twice, not fourteen test entries. Both runs recorded target
execution as `NOT_RUN`; they do not change the formal target result table.

## Resume Gate

A historical release-gated r10 input is retained but is superseded by the
current SDL2 and SDL2_net recipe identities. It has not been transferred or
executed and must not be used as current W3 evidence. Its fail-closed design
required an external publication PASS record before creating any target
evidence or execution root. Historical bundle evidence:

- `fresh-w3-bundle-r10` contains 21 candidate files plus its manifest; generated
  test build directories are explicitly excluded.
- The external r10 freeze record binds the directory manifest, runner, bundle
  generator, validators, and compressed archive without creating a
  self-referential archive hash.
- The archive contains no Python bytecode or cache directories.

The historical missing-gate fixture was rejected before root creation. This is
design evidence only; the published-artifact release-chain W0/W3 remains
blocked and not run, without changing the completed r27 result. A new
release-chain W3 input must be frozen from the final audited candidate after
the SDL2 publication gate is satisfied.

After the dependency publication gate is satisfied:

1. freshly verify `sdl2/2.30.10` with `conan download --only-recipe`;
2. complete the SDL2 dependency shared/static target contract;
3. run fresh shared and static `conan create` on OpenHarmony PC;
4. retain raw logs for all seven unique terminal results in each mode;
5. verify package contents and ELF metadata;
6. run an independent W4 and require P0/P1 to be zero.
