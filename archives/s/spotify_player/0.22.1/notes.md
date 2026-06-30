# spotify_player 0.22.1 - Adaptation Notes

## Build Method: Pre-compiled Binary + gcompat

### Previous Failures
1. rustc SIGSEGV - source compilation failed
2. No aarch64-musl pre-compiled binary on GitHub
3. glibc binary patchelf interpreter change failed (missing 10+ dynamic libs)

### Current Approach: gcompat
Following successful pattern from git-xet/qsv:
- Use glibc binary with gcompat musl shim layer
- Replace glibc NEEDED entries with gcompat equivalents
- Bundle critical missing libs (libasound from Alpine)

### Patchelf Modifications
```bash
patchelf --replace-needed libc.so.6 libgcompat.so.0 spotify_player
patchelf --replace-needed libm.so.6 libgcompat.so.0 spotify_player
patchelf --replace-needed libpthread.so.0 libgcompat.so.0 spotify_player
patchelf --replace-needed libdl.so.2 libgcompat.so.0 spotify_player
patchelf --replace-needed ld-linux-aarch64.so.1 libglibc-shim.so spotify_player
patchelf --set-interpreter /lib/ld-musl-aarch64.so.1 spotify_player
patchelf --set-rpath ~/usr/local/lib spotify_player
```

### Key Findings
- libgcc_s.so.1 MUST be musl-built (glibc version has _dl_find_object@GLIBC_2.35)
- libasound.so.2 from Alpine (musl) works perfectly
- libdbus-1.so.3 stub (22KB) must be replaced with actual library (337KB)
- HMDFS symlinks don't resolve for dynamic linker; must use cp instead of ln -s

### Verification
```
$ spotify_player --version
spotify_player 0.22.1
```

**编译结束**: 2026-06-03
**最终状态**: published (pre-compiled binary, gcompat method)
---

**编译结束**: 2026-06-03 18:59
**最终状态**: published
