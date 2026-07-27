# libldac aosp-20250110 adaptation notes

## Result

- Target: OHOS 6.0, armv8, clang 15 profile
- Date: 2026-07-16
- Status: `built`
- Source revision: `eeee1a3f5f8df1282e3a6d297085885fd886737b`
- Source tree: `d5e246f173f24c2e7743af9091a27d1329fcf2ce`
- Official AOSP archive SHA-256: `acc6dfb98a1089ed14e901e36c4928f311be03d9ec76d5c42e67f8cc9eab932f`
- Read-only mirror archive SHA-256: `e4f07f56e1341113341ff6a5514152ac3c0a36d2d4c54d2d82b16f54d02b916e`

## Implementation

The upstream AOSP snapshot provides Android.bp rather than a standalone build
system. `0001-CMakeLists.txt.patch` adds portable CMake targets for the same
`src/ldaclib.c`, `src/ldacBT.c`, and `abr/src/ldacBT_abr.c` source sets. It
installs `libldacBT_enc`, `libldacBT_abr`, and their two public headers.

The recipe first downloads the commit-pinned archive from the official AOSP
repository and verifies the official archive SHA-256. If that endpoint is
unavailable, it downloads the same revision from Microsoft's read-only AOSP
mirror and verifies the mirror-specific SHA-256. The mirrored commit and Git
tree match the canonical AOSP repository.

No generated configure or build output is stored in the patch.

## Validation

`conan create` completed successfully and produced both static libraries. The
consumer test linked both libraries, allocated encoder and ABR handles,
initialized 48 kHz stereo encoding in SQ mode, and validated the encoder state
through the public APIs before releasing both handles.
