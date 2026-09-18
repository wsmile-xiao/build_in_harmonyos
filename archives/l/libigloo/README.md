# libigloo

libigloo is the common framework library of the Icecast project: a compiled
C library (LGPL-2.0-or-later) with reference-counted objects (`ro`), string
pool (`sp`), locking helpers, PRNG, UUID, digest, time and error interfaces,
plus the TAP mini-framework (`igloo/tap.h`) that Icecast and its consumers
use for testing.

The package is a real compiled library — it is neither header-only nor a
test-framework-only package. `igloo/tap.h` is one public header among
sixteen; `make check` builds 10 test programs against the compiled
libigloo library.

## OHOS adaptation

- Autotools package; the official v0.9.5 tag tarball ships no generated
  `configure`, so the recipe runs `autogen.sh` (autoreconf) first.
- `m4/pkg.m4` (exported alongside the recipe) is copied into `m4/` before
  autoreconf so `PKG_CHECK_MODULES` expands; otherwise configure fails with
  the "possibly undefined macro" cascade (knowledge base E089).
- HarmonyOS (`linux-ohos`) detection patches for `build-aux/config.guess`
  and `build-aux/config.sub` are applied AFTER autoreconf, because
  autoreconf installs the stock automake-1.18 copies that lack HarmonyOS
  support.
- rhash/1.4.6 (digest backend) is a hard dependency. The ohpcd rhash
  package is static-only and non-PIC, so libigloo links it statically
  (`shared=False` default; `shared=True` is rejected in `validate()`).
- Upstream TAP test suite runs in `build()` via `make check`:
  10 test programs, 763/763 assertions PASS on OHOS aarch64.

## Dependencies

- `rhash/1.4.6` — digest computation backend (configure.ac:105).
- System: pthread, libm (part of OHOS bionic libc).
- Build-time: automake/1.18, libtool/2.5.4 (autoreconf bootstrap).

## References

- https://gitlab.xiph.org/xiph/icecast-libigloo
- https://icecast.org
