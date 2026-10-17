# irrlicht 1.8.5

Irrlicht 1.8.5 is built with the upstream `source/Irrlicht/Makefile` targets
`sharedlib` and `staticlib`.

The upstream Linux Makefile branch links desktop X11/OpenGL libraries
unconditionally. OHOS validation uses a headless/null-device build instead:
the recipe injects `NO_IRR_COMPILE_WITH_*` macros for X11, SDL, framebuffer,
OpenGL/OpenGLES, Direct3D, Windows and OSX devices, and the patch removes the
Linux desktop X11/OpenGL link flags from the Makefile.

Three recipe blockers were fixed during OHOS validation (all covered by the
two patches under `patches/`):

1. **Include path lost** — upstream Makefile has no `%.o:%.cpp` compile rule,
   so `.cpp`→`.o` falls through to make's `<builtin>` rule which only honors
   `$(CXXFLAGS)`, not `$(CXXINCS)`/`$(CPPFLAGS)`. The recipe's
   `CPPFLAGS="..."` therefore never produced `-I../../include` on the compile
   line and every source reported `fatal error: 'IrrCompileConfig.h' file not
   found`. The recipe now injects the include flags via `CXXFLAGS` instead.

2. **X11 device guard always true** — `IrrCompileConfig.h` line 105 defines
   `_IRR_COMPILE_WITH_X11_DEVICE_` unconditionally; `NO_IRR_COMPILE_WITH_X11_`
   only undefs the separate `_IRR_COMPILE_WITH_X11_` macro. Nine files gated
   X11 device code on `_X11_DEVICE_`, so the guard was always true and X11
   includes leaked in (`'X11/XKBlib.h' file not found`). The
   `0002-x11-device-guard.patch` re-points all 21 references across the nine
   files to `_IRR_COMPILE_WITH_X11_`, which the recipe's `NO_` macro controls.
   The dead `NO_IRR_COMPILE_WITH_X11_DEVICE_` define was also dropped from the
   recipe.

3. **Bundled deps + runtime SO discovery** — upstream `LINKOBJ` bundles its
   own copies of zlib/jpeglib/libpng/bzip2 `.o` files directly into
   `libIrrlicht.so/.a`; those reference internal hidden symbols
   (`inflate_fast`) and NEON helpers (`png_riffle_palette_neon`) that the
   conan-built deps export differently, breaking test_package linking. The
   `0001` patch drops the four bundled object sets from `LINKOBJ` (keeping
   `$(LIBAESGM)` = irrlicht's own aesGladman code) and links the conan deps
   (`-lz -lpng -ljpeg -lbz2`) instead. The test_package executable links
   `libIrrlicht.so.1.8` by soname, but conan's `VirtualRunEnv` only injects
   the deps' lib dirs into `LD_LIBRARY_PATH`, not the just-built package's
   own; the test_package `test()` therefore prepends the irrlicht package
   lib dir to `LD_LIBRARY_PATH` for the run.

The test package compiles and executes a real Irrlicht smoke test. It creates
an `IrrlichtDevice` with `video::EDT_NULL`, checks that the device and video
driver are valid, and asserts that the driver type remains `video::EDT_NULL`.

OHOS validation passed on `ohos-aarch64`:
```
conan create archives/i/irrlicht/1.8.5 --version=1.8.5 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=irrlicht --build=missing
```
exit 0; test_package ran `Irrlicht Engine version 1.8.5`.

W0 dependency preflight passed for `zlib/1.3.2`, `libpng/1.6.58`,
`libjpeg/10`, and `bzip2/1.0.8`; the actual build graph is aligned to
`zlib/1.3.1.1` because `libpng/1.6.58` depends on that revision. `irrlicht/1.8.5`
is not occupied in `ohpcd`.
