# opusfile 0.12 HarmonyOS PC adaptation notes

## Scope

This candidate replaces the historical manual archive record with a reproducible
Conan recipe. It is a mandatory decoder dependency for DOSBox Staging 0.82.2-r1.
The package preserves both upstream libraries:

- `libopusfile`: memory/file decoding and seeking;
- `libopusurl`: `file:`, HTTP, and HTTPS callback support.

HTTP is not disabled. The exact Conan dependencies are `libogg/1.3.5`,
`opus/1.5.2.1`, and `openssl/3.5.6`. The official build contract requires only
`ogg >= 1.3` and `opus >= 1.0.1`; both selected versions satisfy those minimums.
An isolated Conan home installed their published OHOS 6.0/armv8/clang 15
binaries with `--build=never`, so the PR no longer depends on unpublished
recipes.

The published `libogg/1.3.5` recipe predates the repository's current
pkg-config target metadata and generates `libogg.pc` by default, while upstream
Opusfile requires the canonical module name `ogg`. The recipe uses
`PkgConfigDeps.set_property()` to emit `ogg.pc`. The test consumer similarly
normalizes the published libogg/opus CMake names to `Ogg::ogg` and `Opus::opus`
through `CMakeDeps` properties; no dependency artifact is modified.
Because the consumer directly calls libogg and libopus to create its controlled
fixture, the test recipe also declares those two exact references directly.
This prevents Conan from pruning libogg after it has been absorbed into a
shared `libopusfile` and keeps every direct API use represented in the graph.

## Official source and test inventory

- Official archive: `https://downloads.xiph.org/releases/opus/opusfile-0.12.tar.gz`
- Size: `471354` bytes
- SHA256: `118d8601c12dd6a44f52423e68ca9083cc9f2bfe72da7a8c1acb22a80ae3550b`
- Build system: Autotools only; the release archive has no CMake build entry.

`Makefile.am` has no `TESTS`, `check_PROGRAMS`, or `check-local` entry, so the
registered upstream test count is `0`. Its two `noinst_PROGRAMS` are examples:
both require an external valid Opus input and upstream supplies no fixture or
registered execution command. They are not counted as upstream tests.

The Conan `test_package` adds one independent installed-package flow. It creates
a valid one-frame Ogg Opus stream through libogg and libopus, decodes it from
memory through `libopusfile`, writes the same controlled stream in the current
test directory, and decodes its `file:` URL through `libopusurl`. Internal
checks, the two decode paths, and shared/static repetitions are not split into
extra test cases.

## Portability and package contract

- The bundled 2018 `config.guess`/`config.sub` scripts reject
  `aarch64-unknown-linux-ohos`; two contextual patches add only the HarmonyOS
  recognition paths and retain all existing target support.
- Native OHOS builds run `configure` through `/system/bin/sh`, use the system
  `mkdir -p`, and relax only the generated `config.status` scratch-directory
  mask needed on HMDFS. These build-executor paths are selected through
  `settings_build`, so Windows/Linux cross-build executors retain Conan's
  standard Autotools path.
- OHOS shared builds pass both Libtool target variables as
  `-avoid-version -no-undefined`, producing one real `libopusfile.so` and one
  real `libopusurl.so` instead of version-alias copies on HMDFS.
- Shared package ELFs and the real consumer are signed only for native OHOS
  execution. Static archives remain unsigned.

## Knowledge classification

This adaptation claims Path A for the recipe and Path B for one reusable
knowledge addition. E256 isolates a Conan-specific gap: `CONFIG_SHELL` cannot
wrap the first process emitted by `Autotools.configure()`, so a native OHOS build
executor must prefix the official `configure` path with `/system/bin/sh` while
preserving Conan's generated arguments. Cross-build executors stay on the
standard helper path.

The remaining portability work reuses existing repository knowledge rather
than extending E256: E007 covers the GNU triplet scripts, E011/E129 cover the
Autoconf temporary-directory permission issue, and E087/E165 cover general
script execution and interpreter paths. The Libtool output form, Conan
component metadata, and generated consumer fixture are package engineering
details rather than a separate classification barrier.

Classification evidence is recorded in
`reports/knowledge-expansion-evidence.md`.

## Patch representation validation

The two platform-recognition patches were rewritten only to remove blank
context lines that fail the repository's outer `git diff --check`. Their
resulting source is unchanged. The third patch addresses the independently
observed HMDFS `config.status` scratch-directory failure:

- `0001-config-guess-ohos.patch` SHA256:
  `f80ccd89eb820a975514eaa676f43126d4c4ab4bf416525eb60f87132577e1d5`;
- `0002-config-sub-ohos.patch` SHA256:
  `58cdc44839e27d65fbcb21accc0e82831bf9c6d747865b18639f6e72f2114e45`;
- `0003-configure-hmdfs-temp-mode.patch` SHA256:
  `a64f34a6db90e7001acf447fc561169d27b9d76f274378cd3cc6c58761545782`;
- standard Git apply/check, GNU patch 2.7.6 dry-run/apply with `--fuzz=0`,
  and the existing Conan `patch_ng` environment with `fuzz=False` all accept
  all three patches on separate fresh extractions of the official archive;
- Git, GNU patch, and `patch_ng` produce the same 51/51 raw file hashes;
- the old and rewritten platform-recognition patches, replayed with the same
  `patch_ng` engine, also
  match 51/51 raw file hashes. Their sorted `SHA256  relative/path` tree
  manifests both hash to
  `3984daecfde0758458d93a2b0cf2fd5c111186bc541ba8b5eef2b382ab816766`.

This exact source-tree equivalence preserves the existing package and consumer
evidence; it does not convert the target consumer's `NOT_RUN` state into a
runtime pass.

## Current status

Windows-hosted OHOS cross-builds produced complete shared and static packages
for the current dependency set from recipe revision
`07f25a2820df2b7fcc3d7c92fe8708db`. A separate SDK CMake profile compiled and
linked the installed-package consumer against each package with
`--build=never`: shared package revision
`482619996d550663425e5834177947d7` and static package revision
`43c53cc43ae84c8215274e6c9db1a2bc`. Target execution was unavailable in both
cross-build runs and is explicitly recorded as `NOT_RUN`; neither is counted
as a passed runtime test.

The static package was created successfully during the combined r6 command,
but that command later exited nonzero because its Windows Autotools profile
uses an MSYS compiler wrapper that Ninja cannot execute as a Win32 program.
The r7 `conan test` used the SDK CMake profile against the exact cached static
package and completed compile/link with exit code 0. Native OHOS CI uses a
native compiler path rather than this Windows-only wrapper split. No opusfile
publication, current CI result, target runtime pass, or current W4 pass is
claimed.
