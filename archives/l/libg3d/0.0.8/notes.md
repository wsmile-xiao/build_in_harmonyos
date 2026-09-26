# libg3d 0.0.8 adaptation notes

## library profile

- upstream: http://automagically.de/g3dviewer/ (libg3d-0.0.8.tar.gz, 2009-01-16, 788K)
- license: LGPL-2.1-or-later
- build system: autotools with pre-generated configure
- what it does: load and manipulate 3D model files (3DS, OBJ, DXF, LWO, MD2/MD3, VRML, COLLADA, KMZ, ASE, LDraw and more) plus texture and material helpers
- dependencies used here: glib/2.84.0.1, libxml2/2.15.3.1, zlib/1.3.1.1 (all already in repo; versions aligned with the libgsf 1.14.51 precedent)
- optional deps deliberately off: gdk-pixbuf (extra image loaders) and gtk-doc disabled via configure flags; libgsf-backed plugins build only if detected, no hard requirement added
- source sha256: f3de92a8f22448f8574fbfbf79152fd692c0cf21a081086e91c40206e0c7af17 (Debian and Ubuntu .orig checksum for the same 806038-byte upstream tarball)
- conandata url list: Debian mirror, Ubuntu archive mirror, official automagically.de last as fallback; same sha256 for all entries

## porting points

1. PkgConfigDeps plus AutotoolsToolchain; static-only delivery with --enable-static --disable-shared.
2. OHOS cross: keep toolchain --build (native) and ensure single --host=aarch64-linux-ohos (never --build==--host; equal pair forces cross_compiling=no and `cannot run C compiled programs`); runtime config.sub fix adds aarch64 and linux-ohos acceptance for the 2009-era script.
3. configure umask 077 rewritten to 022 for hmdfs; SHELL and CONFIG_SHELL resolved to bash; stdin redirected from the null device; LD_LIBRARY_PATH neutralized.
4. glib static link needs -lintl and pcre2 handling copied from the libgsf precedent (extra_ldflags plus LD_LIBRARY_PATH for conftest).
5. Upstream tests are 4 smoke programs in tests/ (tests/Makefile.am noinst_PROGRAMS: test_lib/test_buf/test_imgdump/test_cxx, no TESTS registration); recipe passes --enable-cxxtest, runs `make -j1 check` to build then executes each program with per-program rc/output verification (test_buf 0x01234567, test_cxx got context). HMBS_UPSTREAM_TEST_RESULT discovered=4 persisted to hmbs_upstream_result.json and re-emitted by test_package (survives Conan cache hits).
6. Consumer test uses only file-independent APIs: context, material, primitive box and sphere, object radius and scale, model new and free; 12 check() assertions, exit code proves result.
7. True-device rounds: /bin/sh forced for SHELL/CONFIG_SHELL plus configure shebang rewrite (profile OHOS bash is inaccessible), TMPDIR pinned to the HMBS writable dir, CC/CXX resolved via PATH; pkg-config wired per the ayatana-ido precedent (probed system binary incl. the HNP preinstalled path, else the in-recipe pure-Python shim over the real PkgConfigDeps .pc files) so AM_PATH_GLIB_2_0 resolves without touching test scope.

8. 2026-09-25 Signal 9 (compile, empty logs): lowered codegen to -O0 -g0 for minimal peak RSS; rewrote _scrub_bad_shell_refs to direct known paths + shallow allowlisted listing (no ancestor cache walks, 500KB cap, heartbeat) so the silent full-cache walk can no longer pin RAM/trip the watchdog. Upstream scope unchanged (4 programs, --enable-cxxtest kept, make -j1).

9. 2026-09-25 round 6 (3rd strategy cycle): prior string-replace config.sub patch was a no-op on the 2008 script (anchors absent) so --build=aarch64-pc-linux-gnu kept failing `machine 'aarch64-pc' not recognized`. New route: wholesale refresh from a modern system config.sub when available, else unconditional HMBS shim after the shebang short-circuiting aarch64/arm64 linux-gnu and linux-ohos triplets before old validation; config.guess learns HarmonyOS; --build canonicalized to aarch64-unknown-linux-gnu.

10. 2026-09-25 test_package `Library 'g3d' not found in package`: root cause is package_info, not the build (main lib + 4/4 upstream programs built OK). CMakeDeps resolves cpp_info.libs only inside this package's own libdirs, so (a) "intl" moved from libs to system_libs (libintl ships with glib/gettext, cf. gom/json-glib/wv precedent), glib cache dir no longer appended to this package's libdirs, libdirs declared as ["lib","lib64"]; (b) package() verifies lib/lib64 holds libg3d.a/.so after install and falls back to copying the real built artifact from the build tree (.libs) into package lib/ when install drops it elsewhere. No test scope change.

11. 2026-09-25 test_package `Imported target libg3d::libg3d includes non-existent path .../p/include`: `make install` delivered no header tree, so default includedirs=["include"] failed CMakeDeps validation. package() now falls back to copying the real upstream include tree (include/g3d/*.h from the source tree) into package include/; package_info declares only includedirs=["include"] (dep headers flow via requires + transitive_headers, absolute dep cache paths removed).

## status

- [x] recipe files complete, uncommitted working tree
- [ ] HarmonyOS PC real-device conan create plus test_package plus upstream check (pending HMBS preflight this round)
- [ ] push and PR only after real-device gates pass
