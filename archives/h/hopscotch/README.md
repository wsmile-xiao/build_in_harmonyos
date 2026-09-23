# hopscotch

hopscotch 0.1.2 is packaged for OpenHarmony as a C99 static library and CLI.

- Library: `include/hopscotch.h`, `lib/libhopscotch.a`
- CLI: `bin/hopscotch`
- Conan reference: `hopscotch/0.1.2`

The recipe uses the upstream raw GNU Makefile with `make -j1` and has no Conan dependencies. Consumers use `CMakeDeps` and `CMakeToolchain`. The upstream `make test` target is not runnable from this release tarball because its external `greatest.h`/`theft` headers are unavailable; the real Conan API consumer is covered separately.
