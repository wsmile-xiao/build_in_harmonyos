# qtshadertools

Qt Shader Tools module provides tools and APIs for compiling and transforming shader code.

## Available Versions

| Version | Status | Date |
|---------|--------|------|
| 6.11.1 | built | 2026-05-30 |

## Dependencies

- qtbase 6.11.1

## Description

Qt Shader Tools includes:
- `qsb` - command-line tool for shader compilation and transformation
- `libQt6ShaderTools` - shared library providing shader baking APIs
- Bundled third-party libraries: glslang, SPIRV-Cross

## Build Notes

For HarmonyOS compilation, the module requires:
- `QT_QMAKE_TARGET_MKSPEC=harmonyos-clang` for CMake platform detection
- A patch for `src/glslang/CMakeLists.txt` to handle HarmonyOS platform in glslang OS-dependent code path