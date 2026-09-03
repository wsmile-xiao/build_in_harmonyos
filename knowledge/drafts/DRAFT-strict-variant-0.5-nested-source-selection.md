# Draft: anchor strict-variant's top-level public tree before nested build projects

> Source event: strict-variant 0.5 HarmonyOS PC adaptation on 2026-09-03.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

The official `strict-variant` v0.5 archive is a header-only C++11 library. Its
public API is at the top-level `include/strict_variant/`, and its upstream tests
are at top-level `test/`. The same archive also contains an unrelated
`bench/eggs-variant/CMakeLists.txt` project.

The automatic source initializer selected that first nested CMake project and
classified the archive as an unrelated build. A successful build of the nested
benchmark would not prove that `strict-variant` was packaged or tested.

## Recommended handling

1. Inventory the archive before accepting a promoted source root.
2. Anchor a header-only recipe to the top-level public include tree and the
   package's own upstream test entry when both are present.
3. Treat a nested CMake/Make project as a candidate only after checking that its
   target names and include paths consume the requested library.
4. Keep upstream target inventory separate from executed results. In this case,
   six targets ran and passed, while the optional Boost Spirit target remained
   one explicit expected SKIP because `boost/version.hpp` was unavailable.
5. Add a real Conan consumer test so package discovery, include paths, compile,
   link, and runtime behavior are checked independently.

## Evidence from strict-variant

- `include/strict_variant/` contains 28 public `.hpp` files.
- `test/Jamroot.jam` registers `variant`, `compare`, `hash`, and `alloc`, plus
  optional `spirit` and the two tutorials.
- `init-build` first selected `bench/eggs-variant`, whose include path is
  `include/eggs`, not `include/strict_variant`.
- The final recipe packages 28 headers and runs the six default targets directly
  because the official wrapper requires an unavailable `b2` or `bjam`.
- The consumer test links `strict_variant::strict_variant` and passes eight
  assertions.

## Relationship to existing entries

E195 covers sibling-directory loss during nested-source promotion, E466 covers
recursive build-marker false positives such as a documentation Makefile, and
E413 covers transparent conditional-SKIP counting. This draft adds the distinct
header-only boundary: a valid top-level public tree must win over an unrelated
nested benchmark, and the package surface must be tied to that choice.

## Boundaries

This draft does not claim that every nested build project is wrong. A nested
project is valid when archive inspection proves that it builds and installs the
requested library. It also does not convert missing tools or optional Boost
headers into PASS; each condition remains explicit in the test manifest.
