# VTK

VTK is an open-source library for 3D computer graphics, image processing, and visualization.

## Description

VTK (Visualization Toolkit) provides a wide range of 3D visualization algorithms, including surface reconstruction, polygon reduction, mesh smoothing, cutting, clipping, and contouring. It supports multiple data formats and offers advanced rendering capabilities.

## Homepage

https://vtk.org/

## License

BSD-3-Clause

## Versions

| Version | Status | Build Date |
|---------|--------|------------|
| 9.4.1   | built  | 2026-05-26 |

## Build Notes

- Uses CMake build system on HarmonyOS
- Built as shared libraries (~150 modules)
- Disabled Python and Java wrapping for simplified compilation
- Disabled testing and examples
- Rendering modules enabled but without X window system support (suitable for headless/offscreen rendering)
- VTK bundles internal third-party libraries (hdf5, netcdf, cgns, exodusII, etc.)

## Dependencies

None (VTK bundles required third-party libraries internally)

## Installation

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- vtk 9.4.1
```