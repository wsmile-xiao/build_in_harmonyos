# corepdf

A lightweight PDF viewer from the CoreApps/CuboCore family, using Qt6 Widgets and poppler-qt6 for PDF rendering.

## Versions

| Version | Status | Build System |
|---------|--------|-------------|
| 1.0 | built | CMake |

## Description

Original corepdf uses Qt WebEngine + PDF.js for rendering. On OpenHarmony, WebEngine is unavailable, so the rendering backend was replaced with poppler-qt6 native API. The build system was migrated from qmake to CMake.

## Dependencies

- qtbase/6.11.1
- poppler/25.12.0.2 (with Qt6 binding enabled)
