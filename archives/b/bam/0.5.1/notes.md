# Notes — bam 0.5.1

## Software Description
bam is a build system based on Lua. It uses Lua scripts (bam.lua) to describe build rules and can compile C/C++ projects. Version 0.5.1 bundles Lua 5.3.3 source directly.

## Build Configuration
- **Source**: https://github.com/matricks/bam/archive/refs/tags/v0.5.1.tar.gz
- **Build system**: Custom Makefile + make_unix.sh (not autotools)
- **Compiler**: clang 15.0.4
- **CFLAGS**: -fPIC -O2 -Wall -pedantic
- **Linker**: /data/service/hnp/bin/ld (system linker, not OHOS SDK lld)
- **Bundled Lua**: 5.3.3 (included in src/lua/, no system Lua dependency)

## Build Issues and Solutions

### Issue 1: SSL Certificate Verification Failed
- **Problem**: ohc-run.py init-build couldn't download from savannah.nongnu.org (SSL cert error) and the URL returned 404
- **Solution**: Downloaded from GitHub archive URL (https://github.com/matricks/bam/archive/refs/tags/v0.5.1.tar.gz), then used --no-download with manually placed tarball

### Issue 2: OHOS SDK lld Linker Dependency on libxml2.so.16
- **Problem**: The default LLVM linker (lld) from OHOS SDK failed with "Error loading shared library libxml2.so.16"
- **Solution**: Used system linker at /data/service/hnp/bin/ld via -fuse-ld=/data/service/hnp/bin/ld flag

### Issue 3: ELF Signing Required for txt2c Tool
- **Problem**: The txt2c tool (generated during build) couldn't execute (exit code 126) due to unsigned ELF
- **Solution**: Used ohc-run.py sign-elf (binary-sign-tool) to sign the txt2c binary before execution. Added os.chmod(0o755) after signing to ensure execute permission.

### Issue 4: Makefile Expects System Lua
- **Problem**: The Makefile uses pkg-config to find system Lua, which is not installed
- **Solution**: Used make_unix.sh approach instead — compiles bundled Lua source (src/lua/*.c) directly with -I src/lua flag

### Issue 5: Python 2 Test Suite Incompatibility
- **Problem**: scripts/test.py uses Python 2 syntax (print statements, exception syntax)
- **Solution**: Ran individual test cases manually instead; all passed except intentional error-handling test

### Issue 6: Conan source() BadZipFile Error
- **Problem**: Conan's get() couldn't determine archive format from GitHub API URL (no .tar.gz extension)
- **Solution**: Added `filename: "bam-0.5.1.tar.gz"` to conandata.yml to help Conan detect tar.gz format

### Issue 7: test_package copy() Error
- **Problem**: test_package's copy() failed because source and destination were the same directory
- **Solution**: Removed copy() calls — test files are already in the test_package directory which is also the build folder

### Issue 8: bam.lua API Incorrect
- **Problem**: Test bam.lua used `Settings.cc = "clang"` which doesn't exist in bam's API
- **Solution**: Used correct API: `NewSettings()`, `Collect()`, `Compile()`, `Link()`, `DefaultTarget()`

## Build Commands
```bash
# 1. Build txt2c tool
clang -Wall -pedantic -fPIC -O2 -c src/tools/txt2c.c -o ~/tmp/txt2c.o
clang -Wall -pedantic -fuse-ld=/data/service/hnp/bin/ld ~/tmp/txt2c.o -o src/tools/txt2c

# 2. Sign txt2c
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf src/tools/txt2c

# 3. Generate internal_base.h
src/tools/txt2c src/base.lua src/tools.lua src/driver_gcc.lua src/driver_clang.lua src/driver_cl.lua src/driver_solstudio.lua src/driver_xlc.lua > src/internal_base.h

# 4. Compile bam (with bundled Lua)
clang -Wall -pedantic -fPIC -O2 -fuse-ld=/data/service/hnp/bin/ld src/*.c src/lua/*.c -o bam -I src/lua -lm -lpthread -ldl -rdynamic

# 5. Sign bam binary
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf bam

# 6. Install (staging + local)
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
cp bam $TEST_PREFIX/$DEFAULT_PREFIX/bin/bam
mkdir -p $DEFAULT_PREFIX/bin
cp bam $DEFAULT_PREFIX/bin/bam
```

## Conan Recipe Notes
- **Build system**: custom (not autotools/cmake)
- **Dependencies**: None (bundles Lua 5.3.3)
- **OHOS-specific**: ELF signing for txt2c, system linker for compilation
- **Compiler**: obtained from Conan conf `tools.build:compiler_executables` (R33 compliant)
- **Platform check**: `self.settings.os == "OHOS"` (R32 compliant)
- **conan-verify**: All 8 gates passed (G0-G4 + L2/L4/L5)

---
**编译结束**: 2026-07-06 16:25
**最终状态**: published
