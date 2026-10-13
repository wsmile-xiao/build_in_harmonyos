# XaoS

XaoS is an interactive desktop application for exploring and rendering fractal images.

## Features

- Explore the Mandelbrot set and other fractals with interactive zooming.
- Render fractal images to files from scripts or command-line workflows.
- Use the Qt desktop interface and bundled example parameter files.

## HarmonyOS adaptation

The HarmonyOS PC build uses Qt 6 Widgets. HarmonyOS requires executable files to carry a valid signature after their final ELF contents are written. The XaoS recipe handles signing its build tool copy and installed executable. Interactive window presentation depends on an active desktop compositor; the 4.3.4 archive verifies native rendering on a HarmonyOS device.

## Dependencies

- Build: Qt 6 Base with Widgets and PrintSupport, Qt 6 Tools with LinguistTools, CMake, and a C++ compiler.
- Runtime: Qt 6 libraries and the Qt platform integration available on the target system.

## References

- Project: <https://github.com/xaos-project/XaoS>
- Source repository: <https://github.com/xaos-project/XaoS>
