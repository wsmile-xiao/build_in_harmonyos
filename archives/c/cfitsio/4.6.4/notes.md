# cfitsio 4.6.4 Build Notes

## Build Method
- **CMake build** (bypassing autotools HMDFS limitations)
- Build directory: build_cmake

## Configuration
```bash
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_BUILD_TYPE=Release \
  -DZLIB_ROOT=$HOME/usr/local \
  -DUSE_CURL=OFF \
  -DM_LIB=-lm
```

## Known HMDFS Limitations Bypassed
1. **cat cannot write stdout** → CMake doesn't use heredoc
2. **umask 077 directory permission** → CMake handles this correctly
3. **autotools config.status fails** → Used CMake instead

## Manual Steps
- Static library built successfully with make
- Utility programs manually compiled due to M_LIB cmake issue

## Testing
- All programs execute successfully:
  - fitscopy: prints usage help
  - fpack: prints usage help
  - funpack: prints usage help
  - Other utilities: functional

## Files Installed
- lib/libcfitsio.a (2.1M)
- include/fitsio.h, fitsio2.h, longnam.h
- bin/fitscopy, fpack, funpack, imcopy, smem, speed, cookbook