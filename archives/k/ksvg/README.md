# ksvg

KSvg — KDE Frameworks 6 Tier 3 library for rendering SVG-based themes with
stylesheet re-coloring and on-disk caching. Base of the Plasma theme system.

- Homepage: https://invent.kde.org/frameworks/ksvg
- License: LGPL-2.0-or-later

## Artifacts

- `libKF6Svg.so` — core library (`KSvg::Svg` / `KSvg::FrameSvg` /
  `KSvg::ImageSet`), QImage/QPainter software rendering path
- `org.kde.ksvg` QML plugin — declarativeimports (`SvgItem` /
  `FrameSvgItem` for Qt Quick scenes), installed to `lib/qml`

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 6.26.0  | built  | First OHOS adaptation; full build incl. QML plugin (qtdeclarative/6.11.1 chain) |
