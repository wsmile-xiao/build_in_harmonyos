# libsndfile 1.2.2 adaptation notes

## Build configuration

- Issue: AtomGit #31
- Branch: `feat/libsndfile-1.2.2-31`
- Build system: CMake
- Status: HarmonyOS aarch64 shadow CI passed
- Library type: static
- External codecs: disabled
- Command-line programs and examples: disabled
- CMake 4 compatibility: `CMAKE_POLICY_VERSION_MINIMUM=3.5`

The recipe uses CMake to avoid the Autotools temporary-file behavior that is
not reliable on HMDFS. It does not hard-code compiler paths, SDK paths, install
prefixes, or user directories; Conan's CMake toolchain supplies those values.

## Dependency boundary

`ENABLE_EXTERNAL_LIBS=OFF` and `ENABLE_MPEG=OFF` keep the recipe independent of
unpublished FLAC, Vorbis, Ogg, Opus, mpg123, and LAME packages. The resulting
library supports the formats implemented directly by libsndfile, including
WAV and AIFF, but not the disabled optional codecs.

The two existing `config.guess` and `config.sub` patches are legacy Autotools
assets and are intentionally not declared by this CMake recipe.

`0003-fix-cmake-autogen-module-path.patch` fixes an upstream CMake bug exposed
when Conan adds its generators directory to `CMAKE_MODULE_PATH`. The upstream
module treated that list as one directory; the patch resolves the helper script
relative to `CMAKE_CURRENT_LIST_DIR` instead.

## Verification

The upstream tree declares 143 CTest entries. The package builds that suite and
runs 12 deterministic core entries that do not require disabled external
codecs. Format-matrix and pipe/stdio cases are excluded from the device gate to
keep the single-package run bounded.

The Conan `test_package` links to `SndFile::sndfile`, validates the version and
WAV/PCM format, writes four stereo frames to an actual WAV file, reopens it,
checks metadata and exact decoded samples, and removes the temporary file.

## W0

The single-package shadow CI passed on commit
`f2707f8869c6d560d848bce0686c705180ac9894`. All 12 selected upstream CTests
passed and the Conan consumer test passed. The gate reported L0, L1, L4, and
L5 as pass; L2 was skipped because this library-only package intentionally has
no `bin/` directory. See `reports/shadow-ci.md` for the auditable run evidence.

The minimal configuration has no Conan requirements because all external
codecs and MPEG support are optional and disabled. On 2026-08-17,
`conan download libsndfile/1.2.2 -r=ohpcd --only-recipe` returned the remote's
missing-package response, so the target reference was unoccupied.
