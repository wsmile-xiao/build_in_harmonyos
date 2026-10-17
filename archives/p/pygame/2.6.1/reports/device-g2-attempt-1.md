# HarmonyOS PC G2 attempt 1

- Date: 2026-09-04
- Device: HarmonyOS PC aarch64, Python 3.12.9, Conan 2.29.1, clang 15.0.4
- Result archive: `output/pygame-2.6.1/pygame-g2-diagnostics.tar.gz`
- Result archive SHA-256: `48579ee07a5a1292e1ae789a6b892dc266d529db06e29df53f237506230dea78`
- Preceding gates: language preflight PASS; W0 15/15 direct references PASS
- G2 exit code: 1

The first graph selected `sdl2/2.30.10.1:shared=True`. Its source build
completed the SDL library and then its auxiliary test link failed:

```text
ld.lld: error: unable to find library -lSDL2
clang-15: error: linker command failed with exit code 1
```

The dependency recipe searched only for `libSDL2.a` while the shared build
placed the library under `build-release/.libs/libSDL2.so`. No pygame source or
consumer test had run at this point. The revised recipe selects the published
PIC-static `sdl2/2.30.10` package and derives its private shared runtime inside
the pygame build, so this dependency test path is no longer selected.
