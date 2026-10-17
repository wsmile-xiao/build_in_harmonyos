# libkdegames 26.04.0.1 notes

## Scope

Fix release for the already-adapted libkdegames/26.04.0 (commit 865d176015,
"KDE Games dependency chain", published to ohpcd as revision
6c2947fbfc8c12b5d33db598b6a31b20 on 2026-09-15). Upstream source is
unchanged (26.04.0). This run (prerequisite run for kjumpingcube-26.04.0,
user decision 2026-09-19) delivers the SONAME/portability fixes that the
current authoritative CI L5 gate requires.

## Why a version bump (R37)

The artifact registry does not support multiple revisions of the same
version. libkdegames/26.04.0 is already published, and this fix modifies
conanfile.py, so per the CI R37/L0j gate the version must be incremented:
26.04.0 -> 26.04.0.1. The 26.04.0 recipe directory in this repository is
left untouched.

## Delta over 26.04.0

1. DT_SONAME missing on libKDEGames6.so / libKDEGames6Private.so
   (L5a) and IMPORTED_NO_SONAME TRUE in KDEGames6Targets.cmake (L5c).

   Root cause (knowledge reuse: DRAFT-cmake-harmonyos-platform-soname-flag,
   DRAFT-libharu-2.3.0-missing-dt-soname): Conan's OHOS profile maps
   os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS, but CMake has no
   Platform/HarmonyOS module, so CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG
   stay undefined and no -Wl,-soname is passed to the linker.

   Fix in generate() (OHOS only):
   - CMAKE_SHARED_LIBRARY_SONAME_C_FLAG / _CXX_FLAG = "-Wl,-soname,"
   - CMAKE_PLATFORM_NO_VERSIONED_SONAME = TRUE (unversioned, relocatable
     SONAME; avoids relative-soname forms, see
     DRAFT-musl-relative-soname-downstream-cwd)

2. DT_NEEDED entries containing absolute conan-cache paths in
   libKDEGames6.so / libKDEGames6Private.so (L5b). The SONAME-less KF6
   6.18.0 dependency artifacts make lld record the IMPORTED_LOCATION path
   verbatim; the artifact could not load outside the build machine.

   Fix in package(): `_sanitize_needed_entries()` rewrites path-form
   DT_NEEDED entries to plain basenames with a minimal in-place .dynstr
   byte patch (pure python; the basename is always shorter than the
   path-form string, so no ELF structure other than the string bytes
   changes). The loader then resolves the dependencies through
   LD_LIBRARY_PATH / runenv_info, which the recipe and its consumers
   provide. Plain soname-form entries (libQt6Core.so.6, libc.so, ...) are
   not touched.

   Tooling notes (both verified by on-device A/B load tests):
   - `patchelf --replace-needed` must NOT be used: it rewrites the
     program header table (10 -> 24 PT_LOAD segments on this artifact)
     and the resulting ELF is rejected by the OHOS musl loader.
   - OHOS enforces valid ELF code signatures (`.codesign` section,
     knowledge DRAFT-7939): any rewritten file gets EACCES on
     exec-mapping ("Error loading shared library ...") until it is
     re-signed. After patching, the recipe strips the stale signature
     with `llvm-objcopy --remove-section .codesign` and re-signs with
     `binary-sign-tool sign -inFile <f> -outFile <f>.signed -selfSign 1`,
     then restores the original file mode.

3. test_package additions (mandatory OHOS-specific cases):
   - test_ohos.cpp: KGAUDIO_BACKEND=openal capability wiring (compile-time
     guard + runtime check), KGameSound WAV load via libsndfile and
     playback start on the openal-soft Null backend (no real audio device,
     knowledge E285), KGameHighscore local write/read roundtrip under the
     user-writable HOME (empty HIGHSCORE_DIRECTORY on OHOS).
   - test_libkdegames (upstream API smoke) unchanged; both tests run
     through the same run_test.sh loader-path wrapper.

Everything else (dependencies, patches-free build, svgz gzip fallback,
kdnssd/6.29.0 outlier, karchive/6.18.0 override) is inherited verbatim
from 26.04.0.

## Verification

Authoritative CI (`ci/conan/build_and_test.sh`, profile
`ci/conan/profiles/ohos-aarch64`) on libkdegames/26.04.0.1 — attempt 5
(`ci-attempt5.log` in the run root): ALL PASS.

- Upstream CTest: 2/2 passed (`libkdegamesprivate-kgamesvgdocumenttest`,
  `libkdegamesprivate-kgamepropertytest`); `tests/kgamepopupitemtest` is a
  manual demo not registered in upstream ctest, excluded from the count.
- Consumer test_package: 2/2 passed — `test_libkdegames` API smoke and
  `test_ohos` (KGAUDIO_BACKEND=openal wiring, openal-soft Null-backend WAV
  load + playback start via KGameSound, KGameHighscore local roundtrip).
- L5 SONAME gate: PASS — both artifacts carry DT_SONAME; 26 path-form
  DT_NEEDED entries sanitized (14 + 12) and re-signed in package().
- L2 skip: no bin/ dir (pure library package).

Prior evidence trail for the 26.04.0 base on this device:

- ci-attempt3.log: conan create passed (2/2 upstream CTest tests +
  consumer smoke), L0/L1 pass, but L5 soname gate failed (5 errors) —
  the motivation for this fix release.
- ci-attempt2.log: authoritative CI on the untouched base 26.04.0 recipe
  blocked by the JC junk gate's full-repo scan hitting pre-existing tracked
  marker files in other packages (archives/c/cloog/0.21.1/.build-closed,
  .staging-verified; archives/k/kics/2.1.20/.staging-verified) that are not
  in the JC5 whitelist — a repo-wide gate/state issue independent of
  libkdegames.
