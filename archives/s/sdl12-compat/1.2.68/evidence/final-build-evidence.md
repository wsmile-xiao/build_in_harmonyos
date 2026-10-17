# Final forced-build evidence

## Reproduction command

```sh
CONAN_HOME=/storage/Users/currentUser/.conan2 conan create \
  archives/s/sdl12-compat/1.2.68 \
  --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build='sdl12-compat/1.2.68@ohpcd/stable'
```

The command above was rerun after expanding the unattended upstream test set from 4 to 14 programs. It forced the current recipe revision from source, executed every listed upstream program with failure propagation, packaged and signed both shared objects, and passed the Conan consumer test.

## Build identity

```text
Recipe revision: 32ffc687e62647ce598ea9a35bf7dccc
Package ID:      92219b911295cbf30b8c778a4da3b51506c9d757
Package revision:c1c3b7ffb60cafef12cbec4a61421938
SDL2 dependency: sdl2/2.30.10#9a6fd1dbbc0ac1eef2a42639df48e3b4:4b977264131a1c74e82bd6bb51b63cc9aadc4cfa#96027f33d6086703ce6fe4e4502533b3
```

## SDL2 relink

The build used the HarmonyOS compiler driver with `-shared -Wl,-z,defs`, a relative `libSDL2-2.0.so.0` SONAME and `--whole-archive` around the pinned PIC `libSDL2.a`. Packaging rejected non-AArch64 ELF, unexpected NEEDED entries, RPATH/RUNPATH, wrong SONAME or missing signature metadata.

## Upstream tests

All 32 upstream test executables were built. The recipe then ran these 14 unattended commands under dummy video/audio drivers; every command exited zero:

```text
./testver
./testplatform
./testerror
./testiconv
./testfile
./testkeys
./testloadso --hello libc.so
./torturethread
./testvidinfo
./testblitspeed --seconds 1
./testsem 2
./testthread
./testtimer 10
./testjoystick
```

Observed functional markers included:

```text
Compiled version: 1.2.68
Linked version: 1.2.68
All data types are the expected size.
test1 OK
test2 OK
test3 OK
test4 OK
test5 OK
Found puts in libc.so
...apparently, we survived. :)
Video driver: dummy
Testing blit speed for 1 seconds...
Finished waiting for threads
Removing bogus timer...OK!
There are 0 joysticks attached
```

The remaining 18 programs were not counted as passing: twelve wait for physical window/input events, two require real audio or CD-ROM, two require OpenGL/GPU and human exit, `testgamma` is explicitly unsupported by the dummy backend, and `testlock` is an externally terminated infinite stress loop. Their per-program classification is included in the PR body and local `evidence/upstream-test-matrix.md`.

## Package and consumer

```text
Full package reference:
sdl12-compat/1.2.68@ohpcd/stable#32ffc687e62647ce598ea9a35bf7dccc:92219b911295cbf30b8c778a4da3b51506c9d757#c1c3b7ffb60cafef12cbec4a61421938

Conan test package:
sdl12-compat consumer test passed
```

The consumer receives the exact Conan package path in `EXPECTED_SDL2_PATH`. HarmonyOS exposes loaded files under an HMDFS alias, so the test matches the unchanged Conan package-directory suffix in `/proc/self/maps` rather than depending on the Conan home name or inode identity across aliases.

Remote CI must be rerun for the new PR head; previous CI #25780 passed the earlier four-program set and is not presented as evidence for this expanded test revision.
