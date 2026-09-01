# Test Report — gnuplot 6.0.3.1

## Build
- Build system: autotools
- Compiler: clang 15 (OHOS)
- Profile: ohos-aarch64
- Configure: `--with-readline=builtin --with-gd --without-cairo --without-lua --without-qt`
- Result: ✅ Build successful

## Dependencies
- gd/2.3.3 (libgd for PNG/JPEG/GIF image output)

## Image Output Tests
| Format | Size | Details |
|--------|------|---------|
| PNG | 22646 bytes | PNG image data, 640 x 480, 8-bit/color RGB, non-interlaced |
| JPEG | 44412 bytes | JPEG image data, baseline, 640x480 |
| GIF | 7814 bytes | GIF image data, version 87a, 640 x 480 |

## Conan Verify
- G0: ✅ PASS (pre-build risk assessment)
- G1: ✅ PASS (recipe completeness)
- G2: ✅ PASS (conan create - clean build)
- G3: ✅ PASS (system same-name library isolation)
- G4: ✅ PASS (product completeness)
- L2: smoke test passed
- L4: security scan passed
- L5: product baseline comparison passed

## Known Issues
1. "Cannot open initial state save file: Permission denied" — non-blocking
2. "Fontconfig error: Cannot load default config file" — uses internal font
3. WebP terminal not enabled (requires cairo+pango+libwebpmux)
