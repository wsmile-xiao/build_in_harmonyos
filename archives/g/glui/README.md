# glui

GLUI is a C++ user interface library which provides controls such as buttons, checkboxes, radio buttons, and spinners to OpenGL applications.

- **Version**: 2.37
- **License**: BSD
- **URL**: https://github.com/libglui/glui
- **Build system**: cmake

## Description

GLUI is a GLUT-based C++ user interface library which provides controls such as buttons, checkboxes, radio buttons, and spinners to OpenGL applications. It calls the user's callbacks when an event occurs, rather than using an event-driven model.

## Published versions

| Version | Status | Date |
|---------|--------|------|
| 2.37 | published | 2026-06-25 |

## Notes for HarmonyOS

- OpenGL and GLUT are not available on OpenHarmony; stub headers were created for headless compilation
- CMakeLists.txt modified: cmake_minimum_required upgraded from 2.8 to 3.5 for CMake 4.x compatibility
- find_package(OpenGL) uses QUIET mode with fallback to stub headers when GL is not found
- Only core library source files are compiled; example programs and tools are excluded
- Three patches generated: CMakeLists.txt adaptation, GL stub header, GLUT stub header
