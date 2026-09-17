# libkdcraw

libkdcraw is the KDE RAW image decoding library wrapper around LibRaw
(thread-safe `KDcrawIface::KDcraw` class). It provides RAW file
identification (`rawFileIdentify`), embedded/half/full preview and
full-image decoding (`loadRawPreview`/`loadEmbeddedPreview`/
`loadHalfPreview`/`loadFullImage`) with `RawDecodingSettings` quality
control and the `DcrawInfoContainer` metadata container. The library is
used by KDE graphics applications such as digiKam, Gwenview and KSquares.

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- The upstream dependency closure is minimal: Qt6 Core+Gui, LibRaw>=0.18
  and ECM (build tool). No KF6 framework library is needed.
- `cmake/modules/FindLibRaw.cmake` (module mode) resolves against the
  conan `libraw/0.22.1` package through CMAKE_PREFIX_PATH/
  CMAKE_LIBRARY_PATH seeded by the recipe.
- No source patches: all adaptations are option/variable level.

## Versions

| Version | Notes |
|---------|-------|
| 26.04.0 | KDE Gear 26.04 line; first OHOS adaptation (task #8242). |
