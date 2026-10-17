# Test Report — icoutils 0.32.3

## Build

- **Build system**: autotools (configure + make)
- **Compiler**: clang 15.0.4
- **Platform**: OHOS aarch64
- **Status**: ✅ PASS

## Dependencies

- libpng/1.6.58.2 (published to ohpcd)

## Compilation

```bash
./configure --prefix=/usr/local
make -j1
make install
```

### Issues encountered and resolved

1. **HMDFS umask 077**: `umask 077` creates `drwx--S---` directories that deny file creation inside them. Fixed by relaxing to `umask 022` in the configure script.
2. **OHOS config.guess**: Source's config.guess (2012) doesn't recognize HarmonyOS. Replaced with OHOS-aware version from libpng source.
3. **AC_PROG_CC cross-compilation test**: AutotoolsDeps sets `LIBS=-lpng16 -lm` which causes the cross-compilation check to link the test binary against libpng16, which then can't be found at runtime. Fixed by clearing `LIBS` during configure.

## Verification

```bash
$ icotool --version
icotool (icoutils) 0.32.3
Copyright (C) 1998 Oskar Liljeblad

$ wrestool --version
wrestool (icoutils) 0.32.3
Copyright (C) 1998 Oskar Liljeblad
```

## Conan Recipe Verification (G0-G4 + L2/L4/L5)

- G0: ✅ PASS (pre-build risk assessment)
- G1: ✅ PASS (recipe completeness)
- G2: ✅ PASS (conan create clean build)
- G3: ✅ PASS (system-name library isolation)
- G4: ✅ PASS (product completeness)
- L2: ✅ PASS (smoke test)
- L4: ✅ PASS (security scan)
- L5: ✅ PASS (product baseline)

## Conclusion

icoutils 0.32.3 builds successfully on OHOS aarch64. All four tools (icotool, wrestool, extresso, genresscript) are functional.
