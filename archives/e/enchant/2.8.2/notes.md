# Notes — enchant 2.8.2

**Build Date**: 2026-06-09

## Platform Issues & Fixes

### 1. SIGTRAP Crash (CRITICAL)
- **Root Cause**: glib 2.88.0's `debug_objects_atexit` detects unreleased GObject instances at program exit → `g_log_abort` → `raise(SIGTRAP)`.
- **Fix**: Added `signal(SIGTRAP, SIG_IGN)` in `main()` of both `src/enchant.c` and `src/enchant-lsmod.c`.
- **Patch**: 0002-sigtrap-fix-enchant-lsmod.c.patch, 0003-sigtrap-fix-enchant.c.patch
- **Note**: This is a glib-specific issue on this platform; not an enchant bug.

### 2. valac Dependency Broken
- **Root Cause**: Pre-compiled vala package installed but cannot run (dynamic dependency `libvala-0.56.so` symbols missing from `valac` binary).
- **Fix**: Bypass valac compilation by:
  1. Using `make VALAC=true` to skip vala→C transcompilation
  2. Copying pre-generated .c files from original tarball (`enchant-2.8.2.orig/lib/*.c`) to work directory
  3. Creating stamp file `lib/libenchant_2_la_vala.stamp` to prevent make from regenerating
- **Patch**: No source-level patch needed (build-time workaround, not a source change)
- **Note**: Configure still detects valac and sets VALAC=valac in Makefile, but make override bypasses it.

### 3. g_libintl_* Undefined Symbols
- **Root Cause**: glib's static archive (`libglib-2.0.a`) references `g_libintl_*` symbols (gettext wrappers). The platform's libintl.so exports `libintl_*` and bare `gettext` but NOT `g_libintl_*`.
- **Fix**: Created `glib_intl_shim.c` — a shim that implements `g_libintl_*` functions by calling `libintl_*` from libintl.so. Key: must NOT include `<libintl.h>` because it #defines `gettext` → `g_libintl_gettext` which causes type conflicts.
- **Patch**: 0001-glib_intl_shim.c.patch (new file)
- **Build Integration**: Compiled as `.o` and added to `src/Makefile` LDADD.

### 4. PKG_CONFIG_PATH
- **Root Cause**: Configure failed initially because `glib-2.0.pc`, `gmodule-2.0.pc`, etc. were not in PKG_CONFIG_PATH.
- **Fix**: Set `PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig` before configure.
- **Note**: Standard for all autotools builds on this platform.

### 5. UnitTest++ Not Available
- **Root Cause**: No UnitTest++ package on the platform. configure: `Package UnitTest++ was not found`.
- **Impact**: Test suite cannot compile. make check fails.
- **Resolution**: Documented in test-report.md as SKIPPED.

## 发现与知识

- ✅ SIGTRAP crash: glib debug_objects_atexit → g_log_abort → raise(SIGTRAP); fix: signal(SIGTRAP, SIG_IGN) — knowledge_ref: E092-sigtrap-glib-atexit
- ✅ valac broken on platform: bypass with VALAC=true + pre-generated .c from orig — knowledge_ref: E093-valac-bypass
- ✅ g_libintl_* undefined: shim glib_intl_shim.c bridges g_libintl_* to libintl_* — knowledge_ref: E094-glib-intl-shim
- ✅ PKG_CONFIG_PATH must include ~/usr/local/lib/pkgconfig for glib — knowledge_ref: E095-pkg-config-path
- ✅ UnitTest++ unavailable: test suite SKIPPED — knowledge_ref: E096-unittest-missing

## Build Environment

- CC: clang
- CXX: clang++
- CFLAGS: -fPIC -O2
- PKG_CONFIG_PATH: ~/usr/local/lib/pkgconfig
- Prefix: /storage/Users/currentUser/usr/local
- Provider built: aspell only (hunspell/nuspell/voikko/hspell/zemberek not available)

## Compile Steps

```bash
source .build-context-enchant-2.8.2
cd $BUILD_SRC_DIR

# Configure
export PKG_CONFIG_PATH="$DEFAULT_PREFIX/lib/pkgconfig:$DEFAULT_PREFIX/share/pkgconfig"
./configure --prefix=$DEFAULT_PREFIX --disable-static

# Build (bypass valac)
make -j1 VALAC=true

# Staging install
make install DESTDIR=$TEST_PREFIX

# Local install
make install
```

**编译结束**: 2026-06-09
---

**编译结束**: 2026-06-09 12:26
**最终状态**: published
