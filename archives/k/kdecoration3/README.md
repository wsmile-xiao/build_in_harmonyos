# KDecoration3

KDecoration3 is the KDE Plasma interface library used by window managers and
decoration plugins to describe and render window frames, controls, shadows,
settings, and theme metadata.

## Features

- Public interfaces for decorations, decorated windows, buttons, and button
  groups.
- Window-decoration settings, borders, shadows, and scale helpers.
- Theme metadata and provider interfaces for discovering decoration plugins.
- A private bridge library used by the public decoration implementation.

## OHOS adaptation

- The KDE platform allow-list is overridden for the OHOS cross-build.
- Public and private shared libraries are installed together and use stable
  SONAME dependencies plus a relocatable `$ORIGIN` RUNPATH.
- Translation catalog generation is skipped when the build environment does
  not provide `msgmerge`; the linked KI18n runtime API remains available.
- Consumer validation runs on the OHOS AArch64 runtime and covers the public
  API, UTF-8 metadata, ABI properties, and dynamic-loader behavior.

KDecoration3 is a library package and does not install a command-line tool, so
no software-level `commands.json` is required.

## Dependencies

- Build: CMake and Extra CMake Modules (ECM)
- Compile and runtime: Qt Base and KI18n

## References

- Homepage and source repository: https://invent.kde.org/plasma/kdecoration
- Release sources: https://download.kde.org/stable/plasma/
