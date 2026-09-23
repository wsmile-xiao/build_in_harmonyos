# pygame 2.6.1 adaptation notes

## Scope

pygame 2.6.1 is a setuptools project containing 202 Python sources and 68 C
sources. The package builds CPython 3.12 extension modules and a
`cp312-cp312-ohos_aarch64` wheel from the official PyPI sdist.

## Source identity

- Project: https://github.com/pygame/pygame
- Release: 2.6.1
- PyPI upload time: 2024-09-29T13:41:34.698108Z
- Archive size: 14,808,125 bytes
- SHA256: `56fb02ead529cee00d415c3e007f75e0780c655909aaa8e8bf616ee09c9feb1f`
- License: LGPL-2.1-or-later

## Dependency decision

The remote currently publishes an OHOS `sdl2/2.30.10` PIC-static package, but
the `sdl2/2.30.10.1` shared recipe has no shared binary and its source test
driver assumes a static archive in a shared build. Rebuilding that dependency
would therefore fail before pygame starts. The recipe consumes the published
static archive, relinks it once with `--whole-archive -Wl,-z,defs` as a private
`libpygame_sdl2.so`, validates its input hash, ELF/SONAME/exported API, NEEDED
allowlist, and absence of RPATH/TEXTREL, then signs and bundles it. The
published SDL_mixer archive is likewise relinked with whole-archive as
`libpygame_sdl2_mixer.so`; this keeps its music registration objects when
setuptools links the extension. Every pygame extension links to the two
uniquely named private runtimes, preserving a single SDL global state without
colliding with system SDL libraries. The SDL_image and SDL_ttf dependencies
remain static archives and link against the same private SDL2 runtime. Build
and test environments also clear `SDL_DYNAMIC_API`. The Conan consumer clears
it in the final command shell after `VirtualRunEnv` activation and rejects
SDL's override-failure diagnostic, so the optional hook cannot replace the
audited private runtime with an unrelated host library.

The derived runtime input is locked to recipe revision
`9a6fd1dbbc0ac1eef2a42639df48e3b4`, package ID
`4b977264131a1c74e82bd6bb51b63cc9aadc4cfa`, and package revision
`96027f33d6086703ce6fe4e4502533b3`, matching the repository's independently
validated sdl12-compat derivation. A mismatched remote artifact fails during
Conan validation before linking. The pinned package's `libSDL2.a` SHA256 is
`3ff42c3774c40978c48d5d494c71f53f4ecb154afbf2e61861eb69c2986d20c0`.

The private SDL_mixer input is locked to recipe revision
`1e536fb289a65d493119ed5286413696`, package ID
`633084cf454013fd8acab0c0440168f4a9527505`, package revision
`ec63046eebe5dbfc8a1d4cbab6b22c72`, and `libSDL2_mixer.a` SHA256
`92c5c9be00595b1e11c46fff117e1fe32bb018f08f9803f4a0b447a9a4fd734d`.

The newer `sdl2/2.32.10` has verified NativeWindow and OHAudio backends, but its
published static package cannot replace 2.30.10 in this graph without changing
the package IDs of SDL_image, SDL_mixer, and SDL_ttf. A Conan override probe
resolved all three add-on binaries as `Missing`; rebuilding or republishing
them belongs in separate atomic dependency tasks under W0/R36. This version
therefore keeps the fully published 2.30.10 dependency line and records
visible-window support as a runtime boundary.

Required dependencies were checked with `conan download REF -r=ohpcd
--only-recipe`. PortMidi 2.0.8 was not present in the remote, so the optional
MIDI extension is omitted. X11 clipboard and Linux V4L2 camera modules are also
omitted because their platform providers do not apply to HarmonyOS PC.

The published SDL_mixer package intentionally keeps WAV and built-in minimp3;
Vorbis/OGG and other optional decoders are absent. The upstream runner probes
the installed capability and reports only OGG cases as explicit skips, while
WAV/MP3 cases remain executable. A missing PortMidi import is handled the same
way for the noninteractive MIDI cases.

The recipe selects the published `libpng/1.6.58:shared=True` binary and bundles
it through the same signed runtime closure. It shares the published
`zlib/1.3.1.1` closure used by the existing `libtiff/4.7.2` binary. The first
graph had forced libpng `shared=False` and zlib 1.3.2, which needlessly selected
missing package IDs and dependency source rebuilds. The libpng recipe suffixes
`.1` and `.2` package the same upstream 1.6.58 source but use zlib 1.3.2; they
do not form a fully published binary closure with the existing libtiff package.
The runtime bundle preserves notices from both conventional Conan layouts
(`licenses/` and `share/licenses/`) plus root/doc license files. Packages that
omit a notice use complete, hash-checked notices from their exact upstream
release, exported with this recipe. SDL_image, SDL_mixer, and SDL_ttf supply
their exact notices through `share/licenses`; libjpeg-turbo supplies
`doc/LICENSE.md` and `doc/README.ijg`. Exported fallback provenance is:

- SDL 2.30.10 `LICENSE.txt` from
  `https://raw.githubusercontent.com/libsdl-org/SDL/release-2.30.10/LICENSE.txt`:
  upstream SHA-256
  `9b9e1764f06701bcf7ce21e942c682d5921ba0900c6fca760321b1c8837a9662`;
  LF/trailing-whitespace-normalized bundled SHA-256
  `a0e8ce06504966e45088ee1cc7583cc8af9aac615d4cf56d47d847da9cb15139`
- libpng 1.6.58 `LICENSE` from
  `https://raw.githubusercontent.com/pnggroup/libpng/v1.6.58/LICENSE`:
  `bdb0a645ea18c60507d0368379b1ac5474b92255fcc2d115e07486a7672ba526`
- FreeType 2.14.3 `LICENSE.TXT` and `docs/FTL.TXT` from tag `VER-2-14-3`:
  `bd36c8b474855fa294c2ec5c184544478ef3720aad37d65a6296a4f264fd2d3b`
  and `5a5ee54c5001bbad1cdc1a57cc3dd4c42199b2da09d39c7ee41fab002d02967f`
- libtiff 4.7.2 complete `LICENSE.md` from tag `v4.7.2` (including the
  `tif_lzw.c` Berkeley notice):
  upstream SHA-256
  `0e27c2382d7b8147972bbb746e04059a1152c8d0fda9d03ef1399d1a433c4ade`;
  trailing-whitespace-normalized bundled SHA-256
  `b6704cc58ca31d3f4048218772bac575dd579666553afdd3524be0b6b069f3c9`
- libwebp 1.6.0 `COPYING` from tag `v1.6.0`:
  upstream SHA-256
  `5aec868f669e384a22372a4e8a1a6cd7d44c64cd451f960ca69cc170d1e13acf`;
  normalized-final-newline bundled SHA-256
  `e293d1dddc9785200b1f58a4f5293543cf8566d9e0b8a3c02fad955035b19f42`
- zlib 1.3.1 `LICENSE` from tag `v1.3.1`:
  `845efc77857d485d91fb3e0b884aaa929368c717ae8186b66fe1ed2495753243`
- zstd 1.5.7 `LICENSE` from
  `https://raw.githubusercontent.com/facebook/zstd/v1.5.7/LICENSE`:
  `7055266497633c9025b777c78eb7235af13922117480ed5c674677adc381c9d8`

The published libtiff binary uses jpeg, zstd, WebP, xz, and zlib. The recipe
iterates Conan's complete host dependency view, so it collects the actual
transitive runtime rather than over-declaring possible future libtiff
dependencies. The current OHOS graph resolves all 10 direct dependencies and
the xz/zstd transitive closure to published binaries. A post-signing
`DT_NEEDED` audit rejects any third-party SONAME absent from `pygame/.libs`.

## Build design

1. Download and verify the official pygame sdist.
2. Relink the published PIC `libSDL2.a` once as private `libpygame_sdl2.so`; reject
   a non-ELF/non-AArch64 result, wrong SONAME, missing public SDL API, or an
   RPATH before any pygame extension is built.
3. Extract pinned setuptools 75.3.2 and wheel 0.45.1 build wheels into a
   build-private directory.
4. Generate pygame's `Setup` file through its own `buildconfig.config` API with
   Conan dependency include/library paths.
5. Build an OHOS-tagged wheel with the profile compiler and explicit shared
   libpython linkage required by musl BIND_NOW.
6. Install the wheel into package-local staging, bundle the dynamic C-library
   closure and dependency licenses, sign every ELF, add package-relative RPATH
   lookup, and repack the signed wheel with a fresh RECORD.
7. Delete the first staging tree, reinstall the exact repacked wheel, repeat the
   layout and `DT_NEEDED` audits, then run the complete installed upstream test
   entry point with dummy video/audio and the pinned community NumPy 2.2.6 OHOS
   wheel. Real runtime probes report unavailable system fonts, PortMidi, OGG,
   and SDL_ttf shaping without injecting replacement providers.

The result parser is fail-closed: it requires the exact 1,855-case runtime
inventory, all 44 scheduled module names, 14 upstream expected failures, the
single upstream `scrap_test:ignore` module exclusion, and only the declared
capability adjustments. Its skip total must equal the 45 dummy-driver/upstream
baseline skips plus the reported system-font, PortMidi, and pure-OGG skips.
An earlier device run showed one queue-stop failure. SDL_mixer 2.8.1 stops
the current sound before invoking pygame's finished callback, which restarts
the still-queued sound. The generated source patch fixes queue ownership before
`Mix_HaltChannel`; the upstream queue test remains unmodified, including its
immediate post-stop assertion. No extra wait or skip is introduced. The
corrected target run subsequently passed that original test and the consumer's
immediate stop/queue assertions.

The follow-up source correction is now an auditable upstream patch generated
with `refresh-patch --auto`: `src_c/mixer.c` detaches `channeldata.queue` under
the GIL before calling public `Mix_HaltChannel`, and `endsound_callback` acquires
the GIL before checking or moving the queue. This prevents SDL_mixer's finished
callback from restarting a queued sound after `Channel.stop()` and avoids any
private SDL_mixer API dependency. The patch passes dry-run against the exact
pygame 2.6.1 sdist.

No other source patch is applied. The glibc scan hit in `src_c/rwobject.c`
already has a portable fallback: glibc uses `lseek64`, while other libc
implementations, including musl, use POSIX `lseek`.

## Host reference evidence

The official Windows pygame 2.6.1 wheel was tested with the upstream command
`python -m pygame.tests -v`, `SDL_VIDEODRIVER=dummy`, and
`SDL_AUDIODRIVER=disk`:

- 1,855 discovered
- 1,794 ordinary passes
- 14 upstream expected failures
- 47 upstream skips
- 1 module excluded by the upstream `ignore` tag (`scrap_test`)
- 0 failures, 0 errors, 0 unexpected successes
- exit code 0

The sdist build probe reached dependency discovery and then stopped at the
host prerequisite `Microsoft Visual C++ 14.3 or greater is required`. These are
Windows pre-development results, not HarmonyOS validation.

## HarmonyOS validation

The recipe is built and verified on an aarch64 HarmonyOS PC with CPython 3.12.9
and OHOS Clang 15.0.4. Selected run `20260905T181436Z-54433` passed G2, W3,
the standalone consumer, and its negative control. Its `.ci-result.json` has
integrity hash `3eece1eee3fba97e`; the independently
recomputed W3 log SHA256 is
`fb2439568a14381e58a79392dc95f3108ed83faed32bbf3083471241abd81c45`.

The first target G2 attempt on 2026-09-04 passed Python language detection,
source SHA verification, and W0 for the initial 15-dependency graph. It then
stopped while
rebuilding `sdl2/2.30.10.1:shared=True`: that dependency's test helper searched
only for `libSDL2.a` although the shared build had produced `libSDL2.so`, so its
manual test link failed with `ld.lld: unable to find library -lSDL2`. The
current recipe avoids that dependency configuration by consuming the already
published `sdl2/2.30.10:shared=False` PIC package and deriving the private
SDL2/SDL_mixer runtimes inside pygame. Later target runs verified this design.

The full diagnostic archive for that attempt is retained at
`output/pygame-2.6.1/pygame-g2-diagnostics.tar.gz` (SHA-256
`48579ee07a5a1292e1ae789a6b892dc266d529db06e29df53f237506230dea78`); the
concise report is `reports/device-g2-attempt-1.md`.

The next target run reached pygame compilation and exposed a header-root
metadata gap: SDL-family headers are installed in `include/SDL2/`, while the
published Conan metadata exposed only `include/`. The exact failure and fix are
recorded in `reports/device-g2-attempt-2.md`; the recipe now adds that concrete
directory when present.

The diagnostic archive `999pygame-device-results.tar.gz` (run
`20260904T181656Z-10027`, SHA256
`c07a07d70ac0edccfdc21888b8d0a9e4b90ad534479ebf6f717af5037ed44d1`) reached
the final signed wheel and ran all 1,855 upstream cases, then reported 12
failures and 36 errors. The causes were missing `fc-list`, the absent PortMidi
extension, SDL_mixer's unextracted music registration objects, its deliberate
OGG feature trim, and one queue-stop failure. The subsequent device run
`20260905T105823Z-5672` reached 1,855 cases with only the queue-stop failure
remaining. `reports/device-g2-attempt-4.md` records the source-level fix and
`reports/stop-patch-verification.md` records host checks.

The corrected W3 run executed the exact 1,855-case, 44-module inventory: 1,768
ordinary passes, 14 expected failures, 73 declared skips, and no failures or
errors. The 73 skips comprise the 45 upstream/dummy-driver baseline plus 15
system-font provider, 8 PortMidi, and 5 pure-OGG capability skips. Three mixed
OGG/WAV cases retained and executed their WAV branches, and the SDL_ttf shaping
case exercised its real unsupported-feature path. The packaged consumer passed
34/34 assertions, including immediate `Channel.stop()` idle state and an empty
queue. `reports/device-g2-attempt-5.md` records the selected evidence archive.
An earlier run revealed that Conan's `VirtualRunEnv` layer could reintroduce an
`SDL_DYNAMIC_API` value after the environment context removed it. The final run
verified the correction: the consumer clears it in the final shell layer, its
structured marker reports `sdlDynamicApiClean=true`, and neither W3 nor the
standalone consumer log contains the SDL override diagnostic.

The standalone target probe passed 34/34 assertions with exit code 0. Its
negative control repeated the 34 functional passes, failed injected assertion
35, and returned 1. The selected signed wheel is 17,507,956 bytes with SHA256
`5fb4cdcfa7f56461b00a612c2c79086bd4066ca5efb459bff4314eb18c2c6246`.
The complete result archive returned 0 and has SHA256
`fefe05fe105950512d39bfae50353dbbd43a3d6d0c8a90c9b0b9983057fe1283`.

Official CI build `#40901` exposed a packaging-mode defect after the source
recipe passed compilation: the second pip installation produced a
non-executable `pygame/base...so`, causing `Permission denied` on import. The
first follow-up added ZIP mode normalization and post-install execute checks.
CI build `#40908` then showed that mode bits were correct (`35` executable
ELFs and verified wheel modes) while the loader still returned `EACCES`. The
worker's HMDFS UID mapping was the remaining boundary: extracted files carried
the build tree's app UID while the Python loader used another app UID. The
current recipe keeps best-effort UID/GID and mode diagnostics in its own staging
tree, then recognizes the HNP AppSpawn E212 fingerprint and performs strict
read-only ELF/signature/ABI/wheel checks instead of claiming runtime cases. The
consumer tries the real 34 assertions first and uses the same read-only static
fallback only for E212. The new evidence is in
`reports/ci-40908-ownership-fix.md`. Official CI build `#40925` on
`OpenHarmonyPCDeveloper-CI-032` then passed Conan, L0, and L1 for commit
`14c4597d6`; its HNP worker used the documented E212 static path while the
standalone device evidence supplied the full runtime counts. The package is
now marked `built`.

The device run used repository baseline `f5131ee224ce0f5028e6bba671ea1a1f23342f35`.
Before final audit, the task branch was rebased to current `upstream/main` at
`dfe3d3ac77fa7afa801d0a7223122e63f43802c3`. The intervening changes do not
touch pygame or any selected dependency recipe. The only target-profile change
restores the OHOS LLVM `libxml2` loader path; the CI package-loop change extends
the root-file allowlist. The delivery runner now pins the final baseline, and
the patch and W4 inputs are regenerated against it.

No new knowledge draft is added. The dependency test's static/shared artifact
mismatch is covered by E353, the single-runtime decision by E457, the PIC
shared-link proof by E539/E541, and the Python linking/signing/runtime test
path by E004/E077/E212/E472.
