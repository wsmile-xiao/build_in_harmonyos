# Attica KF5

Attica is the KDE Frameworks client library for Open Collaboration Services (OCS).

## Features

- Access OCS providers and their service metadata.
- Model accounts, categories, content, projects, and jobs.
- Provide Qt-based asynchronous network APIs for KDE applications.

## OpenHarmony adaptation

- Published as the `attica-kf5` Conan package for HarmonyOS PC AArch64 with Conan and CMake.
- Uses Qt 5 Core and Network at runtime; Qt host tools are required during the cross-build.
- Cross-built Qt test programs must be executed on an AArch64 target, not on the Windows host.
- HMDFS target ELF files must be signed at their final target paths before execution.
- The network-dependent provider test is reported separately when the external OCS response is empty or unavailable.

## Dependencies

- Build dependency: ECM 6.20.0.
- Runtime and build dependency: qt5-qtbase 5.15.2.

## References

- Homepage: https://invent.kde.org/frameworks/attica
- Source archive: https://download.kde.org/stable/frameworks/5.116/attica-5.116.0.tar.xz
