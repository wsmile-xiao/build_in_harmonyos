# Nuklear

Nuklear is a small ANSI C immediate-mode graphical user interface library. The
package provides the upstream single header `nuklear.h` for downstream projects
that define `NK_IMPLEMENTATION` in one translation unit.

## Package Contents

- `include/nuklear.h`
- upstream license text
- upstream README as packaged reference material

## OpenHarmony Adaptation

- Header-only package; no source patch is required.
- Non-Windows consumers link `m` because the implementation uses math helpers.
- `test_package` compiles and runs a C consumer that calls Nuklear public APIs.
