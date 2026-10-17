# libncursesw/6.6_p20260516: device evidence and knowledge candidates

## Provenance

The tested implementation is commit
`ecce6bcdd8093895839faffe9a13051d8576d1e3` on branch
`feat/libncursesw-6.6_p20260516`. Source is ncurses 6.6 (2025-12-30),
`ncurses-6.6.tar.gz`, SHA-256
`355b4cbbed880b0381a04c46617b7656e362585d52e9cf84a67e2009b749ff11`.
The target is the authorized HarmonyOS PC aarch64 host at
`10.195.180.238:2222`; the device run used its OHOS clang toolchain and GNU
bash, gawk, sed, expr, and pkg-config tools from the project's Conan packages.
These build tools are environment prerequisites, not package dependencies.
Knowledge source and delivery PR: [!10433](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/10433).

The device runner archived that commit to an isolated checkout and Conan home,
then executed the repository's `ci/conan/setup.sh` and
`ci/conan/build_and_test.sh` for
`archives/l/libncursesw/6.6_p20260516` (task type `pr`). It substituted only
the device-specific toolchain profile in the isolated checkout. Neither the
committed CI scripts nor the source tree were changed to fit the device. This
is **local device shadow CI**, not the official GitCode PR CI.

Run ID: `ecce6bcdd809-20260916T144447Z-21138` (2026-09-16
14:44:47-14:55:15 UTC), remote directory:
`/storage/Users/currentUser/ohpc-ci-shadow/runs/ecce6bcdd809-20260916T144447Z-21138`.
The logs require access to that authorized device; this report includes
verifiable excerpts and hashes so the PR does not rely on an opaque run ID.

| Remote evidence | SHA-256 |
|---|---|
| `logs/build_and_test.log` | `ea97a57105d6a4ed11658bc3fe56d2b8373ee141ff82d6cd1b96505bcc48edc9` |
| `gate-results.txt` | `85c402454bff4b4b9407873cc93c53675978a8cf6df358d597f4ad77bb19d2bf` |
| `ci-metadata.json` | `4e7df2a985f1687334407a8effacd36e6b31aa8ff0193038d2ab46d8c2d699` |

## Results

| Layer | Inventory / observed outcome | Boundary |
|---|---|---|
| Upstream `test/programs` | 86/86 program **build entries** built | These are not 86 test assertions. |
| Upstream check | Full `make -j1 check` completed | Upstream assertion inventory is not reported by the build. |
| Installed consumers | 8/8 workflows ran: 2 direct C + `ncursesw6-config` + 5 `.pc` modules | Direct consumers reported 6/6 and 3/3 assertions. Each of six metadata consumers reported 3/3; total 27/27 internal assertions. The earlier `ncurses/6.6` package already had these same workflows; they are not a new knowledge mechanism. |
| Negative configurations | 2/2 observed expected failure: `shared=True` -> ConanInvalidConfiguration, exit 6; missing terminfo -> `FAIL: newterm with packaged terminfo`, exit 1 | Negative-test success does not mean these configurations are supported. |
| Artifacts | Five static archives, 2,874 terminfo files, zero bundled `.so`; `tic` is ELF64 AArch64 with only `libc.so` as a dynamic dependency | Other system/runtime combinations were not tested. |
| Gates | L0, L1, L2, L4, L5 passed; single-package summary 1/1, process exit 0 | L2 emitted nonblocking `--version`/`--help` warnings for ten upstream commands. Official PR CI and AI review are separate and pending. |

Selected log lines (Conan's package prefixes omitted from metadata lines):

```text
libncursesw/6.6_p20260516: OHOS_BUILD_TOOLS=8/8
libncursesw/6.6_p20260516: UPSTREAM_TEST_PROGRAMS=86/86
UPSTREAM_CONSUMER_CORE=6/6
NCURSES_COMPONENTS=3/3
METADATA_CONFIG_LINKS=libncursesw.a
METADATA_PKGCONFIG_FORMW_LINKS=libformw.a,libncursesw.a
METADATA_PKGCONFIG_MENUW_LINKS=libmenuw.a,libncursesw.a
METADATA_PKGCONFIG_NCURSESXXW_LINKS=libncurses++w.a,libncursesw.a
METADATA_PKGCONFIG_NCURSESW_LINKS=libncursesw.a
METADATA_PKGCONFIG_PANELW_LINKS=libncursesw.a,libpanelw.a
  Pass rate: 100.0% (1/1)
```

The positive run also logged a failed source pre-download followed by a Conan
download of the hash-checked source. Configure emitted warnings for feature-test
macros and `MB_LEN_MAX`; no related build or consumer failure was observed.
The linker-trace archive order shown above is trace output, not the argument
order; consumers link dependent archives before the core provider.

## Knowledge extraction

| Candidate | Trigger and cause | Observed contract and repair | Closest material / proposed disposition |
|---|---|---|---|
| Build tool PATH and archiver selection | An absolute compiler path can work while later `make` still resolves `ar` through PATH or the Conan profile; the device runner's GNU tool directories must survive the recipe environment. | On a failed shadow run, `make[1]: ar: No such file or directory` stopped static archiving (exit 127). Supplying an explicit target `AR` and GNU tool paths in the isolated device profile let the same source HEAD pass; the final recipe also preserves inherited PATH and composes `VirtualBuildEnv`. | E540 already covers compiler paths working while runner PATH drops `make`; E012 already covers configuring LLVM `AR/RANLIB/NM/STRIP`. This draft **supplements E540** with the recipe-PATH boundary and failure evidence, while reusing E012, not claiming a new archiver fix. Profile and recipe changed across the final comparison, so single-change causality is not claimed. |
| Static metadata and archive closure | A `.pc` or config script can report plausible `-I` and `-L` flags without proving which archives linked. | Six target consumers isolated `PKG_CONFIG_LIBDIR`, traced packaged static archives with `-Wl,-t`, and ran using packaged terminfo. | `ncurses/6.6` already has the same six metadata consumers and static artifact verification. Reused verification, **not** new knowledge. |
| Terminfo resource availability | Library APIs may need terminal data at runtime. | Package 2,874 files and set `TERMINFO`/`TERMINFO_DIRS`; the empty-terminfo consumer fails. | Existing terminfo-bundle and OHOS musl terminfo drafts already cover the mechanism. This is a verified application case, not a new knowledge ID. |
| Build-shell and GNU tools | Device defaults lack the tools required by Autotools ncurses. | Use available GNU build tools and the configured shell. | Existing Autotools/OHOS shell drafts cover the mechanism; this is an adaptation prerequisite, not a new pattern. |

Search scope: `knowledge/graph/`, `knowledge/drafts/`, and the existing
`archives/n/ncurses/6.6/` recipe; queries included `ar: No such file`, `PATH`,
`E540`, `E012`, `terminfo`, `TERMINFO_DIRS`, `PKG_CONFIG_LIBDIR`, `static`, `shadow`,
`ncursesw6-config`, and `pkg-config prefix`. E540 covers the existing runner
PATH mechanism, and E012 covers missing LLVM `ar`. The original `ncurses/6.6` reference also already supplies
the same static metadata and consumers. An actual metadata archive-selection
failure has **not** been observed here; it is not claimed as new knowledge.

The retained failed device shadow run at the **same** earlier source HEAD
`2b07bb5f6285` was
`2b07bb5f6285-20260916T141029Z-51777`, with
`logs/build_and_test.log` SHA-256
`9dadb113b4415b5eb29a70dc4d38f274c9915c5d6a479296b7d4bf6cc03bd27f`.
The successful run of that same HEAD was
`2b07bb5f6285-20260916T142420Z-64228`, log SHA-256
`d97a00395bd4b5ea4f9cf41a829d3c64870fdc36d61b014aec3f7efe419f6c66`.
Both logs are under the same device run root as the final run, keyed by run ID.
The failed run reported:

```text
ar unknown ../lib/libncursesw.a
make[1]: ar: No such file or directory
make[1]: *** [Makefile:1010: ../lib/libncursesw.a] Error 127
```

The successful same-HEAD run invokes the target toolchain's `llvm-ar` at the
same archive step. The device's isolated profile and tool bootstrap changed
between those two runs; the final `ecce6bcdd809` recipe also preserves the
incoming PATH while composing the Conan build environment. These comparisons
establish a previously missing archiver in the tested environment and the
working configuration, **not** that the recipe change alone resolved it.
No official PR CI or AI-review result is represented by these local runs.
