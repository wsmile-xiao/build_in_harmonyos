# SLiM 1.3.6 - Build Notes for HarmonyOS NEXT

## Overview
SLiM (Simple Login Manager) is an X11-based graphical login manager. This build
targets HarmonyOS NEXT (HongMeng Kernel 1.12.0, aarch64, musl libc, clang 15.0.4).

## Build Status: **SUCCESS** (with limitations)

## Key Adaptations

### 1. Missing X11 Extension Libraries (Xft, Xmu, Xrandr)
HarmonyOS NEXT does not provide libXft, libXmu, or libXrandr. These were replaced
with stub implementations:
- **Xft stub**: All Xft rendering functions return NULL/0. Text rendering in the
  login panel will not work (no font drawing via Xft).
- **Xmu stub**: XmuClientWindow() stub returns the input window (simple fallback).
- **Xrandr stub**: All Xrandr functions return NULL/0, triggering the fallback
  viewport detection in GetPrimaryViewport().

Stub headers are in `X11stub/` directory, implementations in `xft_stub.cpp` and
`xrandr_stub.cpp`, both compiled into `libslim.so`.

### 2. musl libc Compatibility
- `getusershell()`, `setusershell()`, `endusershell()` are not in musl libc.
  Stub implementations provided in `musl_stub.cpp` (getusershell returns "/bin/sh").
- `basename()` requires `libgen.h` on musl (not in `<string.h>` like glibc).
  Added `-DNEEDS_BASENAME` flag.
- Shadow password support (`getspnam`) is limited on musl. Disabled via
  `-DNO_SHADOW_SUPPORT=ON`.

### 3. PAM Disabled
PAM (libpam) is not available on HarmonyOS NEXT. Built with `-DUSE_PAM=OFF`.
This also disables slimlock (which requires PAM).

### 4. CMake Configuration
- `cmake_minimum_required` updated from 2.6 to 3.10 (cmake 4.1.2 compatibility).
- `CMAKE_SYSTEM_NAME=Linux` override needed for FindX11 module to work.
- `CMAKE_POLICY_VERSION_MINIMUM=3.5` added for cmake 4.1.2 compatibility.
- ConsoleKit disabled (`-DUSE_CONSOLEKIT=OFF`).
- X11stub include directory added for stub headers.
- Stub source files added to `common_srcs` and `slim_srcs`.

### 5. Source Code Changes
- `image.h`: Changed `<X11/Xmu/WinUtil.h>` to `"X11/Xmu/WinUtil.h"` (stub header),
  added `#include <X11/Xutil.h>`.
- `panel.h`: Changed Xft and Xmu includes to use stub header paths.
- `panel.cpp`: Changed Xrandr include to stub path, fixed `WinGC < 0` to `!WinGC`
  (GC is a pointer type in X11, not int).
- `app.cpp`: Added `#include "musl_stub.h"` for getusershell declarations.

## Build Configuration
```
cmake \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH=$HOME/usr/local \
  -DUSE_PAM=OFF \
  -DUSE_CONSOLEKIT=OFF \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DNEEDS_BASENAME_FOR_MUSL=ON \
  -DNO_SHADOW_SUPPORT=ON \
  ..
make -j1
```

## Installed Files
- `$PREFIX/bin/slim` - Main executable
- `$PREFIX/lib/libslim.so.1.3.6` - Shared library (with stubs)
- `$PREFIX/share/man/man1/slim.1` - Man page
- `$PREFIX/share/slim/themes/default/` - Default theme files
- `/etc/slim.conf` - Configuration file
- `/lib/systemd/system/slim.service` - Systemd service file

## Limitations
1. **Xft text rendering disabled**: Login panel text won't render via Xft.
   SLiM will need actual Xft library for proper display.
2. **Xrandr multi-monitor disabled**: Falls back to default viewport.
3. **No PAM authentication**: Uses simple password verification instead.
4. **No shadow password support**: Cannot use shadow password database.
5. **No slimlock**: Screen locker requires PAM.

## Compilation Warnings
- `app.cpp:462:9: warning: enumeration value 'Lock' not handled in switch [-Wswitch]`
  (Non-critical, existing upstream issue)

## Dependencies (Available)
- libX11.so.6 + libXext.so.6 (X11 core)
- libfreetype.a (static)
- libfontconfig.so
- libjpeg.so, libpng.so, libz.a
- libpthread

## Dependencies (Stubbed/Missing)
- libXft → stub
- libXmu → stub
- libXrandr → stub
- libpam → disabled
- libcrypt → not found separately (built into musl libc)