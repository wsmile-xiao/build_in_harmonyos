# kdegraphics-mobipocket

KDE library for reading Mobipocket format e-books. Provides the QMobipocket6 shared library.

## Versions

| Version | Status | Build System |
|---------|--------|-------------|
| 26.04.1 | built | CMake (ECM) |

## Dependencies

- qtbase/6.11.1 (Qt6Core, Qt6Gui)
- ecm/6.20.0 (Extra CMake Modules, build-time)

## Description

kdegraphics-mobipocket is a KDE Graphics component that provides a library for
parsing and reading Mobipocket format electronic book files. The library
exposes the `Mobipocket::Document` class which can extract metadata, text
content, and images from .mobi files.

## License

GPL-2.0-or-later
