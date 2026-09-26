# DOSBox Staging on OpenHarmony: test framework and toolchain evidence

## Purpose

This page explains how the official DOSBox Staging 0.82.2 test suite is made
deterministic, executable, and auditable for the OpenHarmony PC adaptation.
Its final values are bound to the accepted r71 W3 evidence and can be reviewed
together with the recipe.

## Toolchain inputs

| Input | Fixed contract |
| --- | --- |
| DOSBox Staging | official `v0.82.2` archive, SHA-256 `387c97b373c3164ab5abbbc2b210bf94b5567057abe44ee1e8b4d4e725bd422c` |
| build definition | Meson, minimum upstream version 0.59.0, C and explicitly forced C++20 |
| package manager | Conan 2.29.1 with OHOS/aarch64 host and build profiles |
| test framework | GoogleTest/GoogleMock 1.14.0 source, SHA-256 `8ad598c73ad796e0d8280b082cebd82a630d73e73cd3c70057938a6501bba5d7` |
| Meson integration | WrapDB gtest 1.14.0-1 patch, SHA-256 `2e693c7d3f9370a7aa6dac802bada0874d3198ad4cfdf75647b818f691182b50` |
| source policy | `wrap_mode=nodownload`; all three downloads are pre-seeded by digest |
| target artifact checks | LLVM readelf/objcopy and the platform signing tool from fixed target paths |

## Why the framework needs explicit preparation

The upstream release has no `.git` metadata, yet Meson runs a shell helper that
queries Git. Unit tests also use a fallback subproject when gmock is not already
available. An unprepared build could therefore fail during configuration or
attempt an untracked framework download. The recipe solves these separately:

1. use the official tag commit as a required release-archive provenance input;
2. pre-seed both framework files in Meson's package cache;
3. forbid configuration-time downloads;
4. enable `unit_tests` only where produced executables can run;
5. inspect Meson's registered test list before execution;
6. sign each generated OHOS test ELF exactly once;
7. execute the Meson suite with one process;
8. validate Meson's persistent JSON terminal log after execution.

The recipe also fails closed if any archive patch or patched C/C++ source uses
an `OHOS`-named preprocessing directive. Platform portability must remain in
POSIX behavior or capability detection, not a platform-name source branch.

## Independent test inventory

There are exactly 24 Meson registrations. The authoritative list is
`test_package/MANIFEST.yml`, cross-checked against upstream
`tests/meson.build` and the validation TSV. Three entries are explicit:

- `gtest example`
- `gtest fs_utils`
- `gtest program_mixer`

The remaining 21 are generated once each from the upstream `unit_tests` table.
The runner does not count GoogleTest assertions, parameter combinations,
source files, repeated configurations, or internal checks as additional test
entries.

## Terminal policy

Meson emits one JSON record per registered test. Records may finish in any
order. The validator normalizes only an exact name or the exact
`dosbox-staging:` project prefix, then enforces all of the following:

- 24 records and 24 unique names;
- set equality with the locked upstream inventory;
- exactly one record for each name;
- terminal result `OK` for 23 records and `EXPECTEDFAIL` for `gtest example`;
- no missing, duplicate, unknown, skipped, timed-out, failed, interrupted, or
  otherwise unknown outcome.

`gtest example` deliberately returns failure and is registered with
`should_fail: true`. It is accepted only when Meson records terminal
`EXPECTEDFAIL`; the raw program exit is never counted as a suite failure by
itself.

## Installed-package flow

After package creation, one installed-package flow starts the packaged
executable and performs four consumer checks. The first checks the bound
version `0.82.2`; it proves package identity and launchability only. The
remaining checks exercise platform capabilities in the application itself:

1. A NativeWindow/OpenGLES2 run validates a decimal surface tuple, the
   `nativewindow` video driver, renderer creation, and a completed
   `SDL_RenderPresent` or OpenGL swap.
2. An OHAudio run selects `SDL_AUDIODRIVER=ohaudio` and requires a callback
   marker after non-zero finite samples from the DOSBox master mixer are
   received. The callback is observational and cannot manufacture samples.
3. A dynamic-core run selects `core=dynamic`, requires entry into the
   production dynamic run function, and requires the guest command stream to
   print `DOSBOX_DYNREC_GUEST_SENTINEL`.

The terminal is accepted only as
`DOSBOX_CONSUMER_FLOW|4/4|PASS`. Dummy/offscreen video, dummy audio, a static
dynrec marker, a missing guest sentinel, or a version-only result is rejected.
All four checks are application-level; standalone provider probes are
diagnostic and cannot replace this flow.

## Fresh-run isolation

The main runner requires a committed candidate manifest, a target-release
record, ten dependency evidence bindings, and a hash-bound closed dependency
cache. The direct evidence table remains ten rows, while the cache contains the
exact 16-reference direct-plus-transitive graph selected by the current
recipes. Its aggregate manifest records recipe/package revisions, package IDs,
package folders, package-manifest hashes, and every regular file and symbolic
link. Bundle preparation and target preflight independently compare that
manifest to the archive. Its execution root, Conan home, temporary directory,
source cache, and project copy must all be absent before start. Conan remotes
are disabled, and only the main reference may be built. Dependency package
files and links are recorded before the build and checked again afterward.

The launcher first executes a read-only preflight. Only after every gate passes
does it claim the unique launch directory and invoke one background runner.
The final evidence manifest uses result-relative paths so it remains replayable
after transfer.

## Validator mutation coverage

Static terminal checks reject missing, duplicate, unknown, over-prefixed,
failed, skipped, and timed-out records. The evidence validator also rejects at
least these mutations: stale file content, missing artifacts, failed main
state, incorrect 24/24 summary, duplicate raw terminal, failed terminal TSV,
changed dependency state, dependency rebuild selector, duplicate signing
section, embedded runtime path, and conflicting final state.

These are validator checks, not substitutes for the 24 official executions.

## Final evidence

| Result | Required final value | Current value |
| --- | --- | --- |
| dependency W0 | complete OHOS/armv8 graph with no missing binary | `PASS (17 nodes, 15 packages downloaded and installed)` |
| upstream Meson suite | 24/24 | `PASS: 23 OK, 1 EXPECTEDFAIL` |
| installed-package capability checks | 4/4 | `PENDING_TARGET_W3` |
| dependency evidence | 16-reference closed cache | `PASS in the r71 closed cache` |
| candidate HEAD | exact SHA | `4966be612920a2a4cb8d39b4970aa3d7b4639eb1` |
| candidate manifest | SHA-256 | `4348bc4e674ba4ac5733fe4a0bef5851f7fe73b198c0861c22cf6eecf56363a0` |
| dependency cache | SHA-256 | `02495c363c77895a2ad04d9b9e8cc98bf1704129a33a230e7dd92d851518926f` |
| packaged AArch64 ELF | signed target binary | SHA-256 `0d272515fadf5e453f6767fba9db7f3c5d8497d9ff7673297a12745166084613` |
| evidence manifest | SHA-256 | `40e3de5e3e88a63e85786a0768ac7fe303eb90f4f6722fb97540e5c49326d15d` |
| transaction terminal | exact identity | `a7bf6ef3a23b286c25bab198c93dad919304c35dc86c3ebc914d959a7737605b` |

The r71 transaction used one launch, finished `POSTRELEASE_PASS`, and was
released with two clean scans. Historical failed or prelaunch successors are
not combined with these results. Platform code findings remain subject to the
AI Review generated after the software PR is created.

The current framework inventory and historical r71 transaction do not exercise
a visible SDL surface, a non-dummy audio sink, or a guest program under dynrec.
The previous version-only consumer is retained as historical evidence and
cannot be used as a capability pass. The new candidate adds the
production-bound checks described above; their target result remains pending
until a fresh signed W3.
