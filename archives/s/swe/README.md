# swe

Swiss Ephemeris high-precision ephemeris library by Astrodienst AG
(Dieter Koch / Alois Treindl).

## OHOS adaptation

- Plain Makefile project, no configure step; the recipe builds the portable
  targets (`libswe.a`, `libswe.so`, `swetest`, `swemini`) with the
  Conan-configured Clang (R33).
- Packages `libswe.a` (plus `libswe.so` with `shared=True`) and the public
  headers; the `swetest` / `swemini` demo tools are built only as build-time
  verification and are not packaged.
- Upstream `setest` harness (10 suites) needs libcrypto + m4 build tools and
  JPL-scale ephemeris data at build time, so the build runs upstream's own
  `swetest` binary in Moshier mode (offline, no data files) as the upstream
  verification, with the uncovered suites recorded as environment gaps.
- Consumer test (`test_swe.c`) covers julday, version, Sun/Moon positions,
  planet names, sidereal time, houses and ayanamsa in Moshier mode, so no
  `.se1` data files are required.

## References

- https://www.astro.com/swisseph/
- https://github.com/aloistr/swisseph
