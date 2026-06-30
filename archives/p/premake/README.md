# premake

Premake is a build script generator that uses Lua scripts to describe software projects. It generates project files for Visual Studio, Xcode, GNU Make, and other build systems.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 5.0.0-beta8 | built | 2026-05-26 |

## Description

Premake uses a self-bootstrapping build system (Bootstrap.mak) that compiles a bootstrap binary from C/Lua source files, then uses it to generate project files for the final build. On HarmonyOS, libuuid is unavailable, so the UUID generation fallback uses /dev/urandom instead.
