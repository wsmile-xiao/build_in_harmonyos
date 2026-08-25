# libnsgif 1.0.0 HarmonyOS PC adaptation

- Upstream build system: NetSurf makefiles using netsurf-buildsystem.
- The package itself contains two library sources: src/gif.c and src/lzw.c.
- No external runtime library dependency is required by libnsgif.
- The Conan recipe builds the original sources directly instead of introducing netsurf-buildsystem as a packaging dependency.
- No upstream source patch is required.
- Upstream test program: test/nsgif.c.
- Upstream test runner: test/runtest.sh.
- Upstream test corpus: 284 GIF files, consisting of 3 regular samples and 281 AFL-generated samples.
- The original upstream test program and runner are compiled and executed during build.
- The consumer test performs 8 checks over creation, scanning, metadata and frame decoding.
