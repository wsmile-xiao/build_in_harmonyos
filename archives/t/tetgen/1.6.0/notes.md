# TetGen 1.6.0 HarmonyOS PC adaptation

## Upstream

- Repository / homepage: https://wias-berlin.de/software/tetgen/
- Version: 1.6.0 (released 2020-08-31)
- License: AGPL-3.0-only (GNU Affero General Public License v3; commercial licensing available from WIAS)
- Language: C++ (two source files: `tetgen.cxx`, `predicates.cxx`, plus the public header `tetgen.h`)
- Third-party dependencies: none; links only the system math library (`-lm`)

## Build

The upstream distribution ships a handwritten Makefile and a minimal
`CMakeLists.txt`. The Makefile rules are used for a deterministic direct build:

1. `predicates.cxx` is compiled at `-O0` (J. Shewchuk's adaptive-precision
   geometric predicates are sensitive to FP optimization).
2. `tetgen.cxx` is compiled at `-O3 -DTETLIBRARY` and archived together with
   `predicates.o` into `libtet.a`.
3. `tetgen.cxx` is compiled again without `TETLIBRARY` and linked with
   `predicates.cxx` + `-lm` to produce the `tetgen` CLI executable.
4. The CLI executable is signed with `binary-sign-tool` so it can run on OHOS.

No upstream source patch is required. The `CMakeLists.txt` in the tarball is not
used because its `cmake_minimum_required(VERSION 2.6)` is incompatible with
modern CMake and it lacks install rules and an explicit `-lm` link.

## Upstream tests

TetGen has no unit-test suite. The bundled 28-point PLC example (`example.poly`)
is used as an end-to-end smoke test: `tetgen example.poly` must exit 0 and emit
mesh output. It runs inside `build()` after ELF signing.

## Consumer test

One Conan consumer executable links the packaged `libtet.a` and drives the
library through the `tetgenbehavior` + `tetrahedralize()` interface. It
tetrahedralizes a 4-point unit tetrahedron and asserts the output contains at
least 4 points, at least one tetrahedron, and an allocated point list (3
assertions). The test_package compiles the consumer directly with the resolved
`clang++` (no CMake helper) because the shadow-CI environment does not expose
`cmake` on PATH.

## Shadow CI evidence (HarmonyOS PC)

- `conan create` passed: 1/1 package built, 0 failed.
- L0 (quality gates, incl. R37 version collision + R38 commands.json): pass.
- L1 (test_package executed; upstream `tetgen example.poly` smoke + consumer
  test "4 points, 1 tetrahedra"): pass.
- L1e (destructive negative test, R34): pass — test genuinely depends on tetgen.
- L2 (CLI smoke `tetgen --version`): pass.
- L4 (no patches): pass.
- L5 (bin/ has content): pass.

## Notes

- Upstream 1.6.0 tarball has no standalone `LICENSE` file; the `README` carries
  the copyright notice and points at the AGPL-3.0 terms. The package copies
  `README` into `licenses/`.
- The packaged `bin/tetgen` CLI is exposed via `cpp_info.bindirs` (R38) and the
  software-level `commands.json`.
- Library name is `libtet.a`, so `cpp_info.libs = ["tet"]`.
