# Draft: OHOS clang does not predefine `_POSIX_C_SOURCE` — declare the POSIX level at compile time instead of editing upstream fallback definitions

> Source event: cheat/1.0.4 adaptation, 2026-09-19. Root-caused on the OHOS
> clang 15 toolchain (aarch64-unknown-linux-ohos).
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

Legacy C test code often guards POSIX-only behavior with:

```c
#elif _POSIX_C_SOURCE >= 200112L
#include <unistd.h>
#else
CHEAT_DECLARE(
    static void sleep(int const seconds) {}
)
#endif
```

On glibc hosts, `features.h` implicitly predefines `_POSIX_C_SOURCE`, so the
POSIX branch is selected and the `#else` fallback never compiles. OHOS's
clang + musl-based libc does **not** predefine `_POSIX_C_SOURCE`, so the
fallback branch is compiled — and the private `static void sleep(...)`
collides with the real `unistd.h` declaration that the same TU already
pulled in (cheat.h enables `CHEAT_POSIXLY` on `__linux__` and includes
`unistd.h`):

```text
tests/jammed.c:22:14: error: static declaration of 'sleep' follows non-static declaration
tests/slow.c:20:14: error: static declaration of 'sleep' follows non-static declaration
```

This is a hard clang error (semantic declaration conflict), not a warning —
no `-Wno-error` flag can downgrade it.

## Measured facts (OHOS device, clang 15, aarch64-unknown-linux-ohos)

- Default compile of `tests/jammed.c` / `tests/slow.c`: hard error above.
- With `-D_POSIX_C_SOURCE=200112L`: both files compile rc=0, run rc=0/1
  per upstream semantics, and the full 25-file `tests/*.c` suite compiles
  25/25 and runs 25/25 with the framework report present.
- `conan-verify cheat 1.0.4`: G1–G4 PASS; W3 local CI: JC/L0/L1 pass.

## Recommended approach

Add `-D_POSIX_C_SOURCE=200112L` to the compile flags of the affected build
(the recipe `build()` upstream-test gate, `CFLAGS`, or `CMAKE_C_FLAGS`).
This mirrors what glibc's `features.h` implicitly provides, so the upstream
`#elif _POSIX_C_SOURCE >= 200112L` branch is selected and the fallback
static definition is never compiled — no source edit, no semantic change to
any test:

```bash
clang -D_POSIX_C_SOURCE=200112L -I . -o prog -w tests/jammed.c && ./prog -s
```

## Fallback

If the fallback definition is genuinely needed for non-POSIX-only builds,
rename the private symbol out of the libc namespace instead of defining a
same-name static function.

## Forbidden shortcuts

- `-Wno-error=...static` / `-Wno-error=...declaration`: hard error, cannot
  be downgraded.
- `#define sleep(...)`: macro-izing cannot reconcile a static definition
  with the real `unistd.h` declaration and silently alters the libc API for
  every including TU.

## Related

- `similar_to`: E032 (`_GNU_SOURCE` for dirent API on musl), E033
  (`_XOPEN_SOURCE` for wide chars), E152 (POSIX timer constants need a
  feature macro), DRAFT-musl-posix-decl-conflict-rename-legacy (getline
  same-name conflict, rename-based fix). All are the feature-test-macro
  family; this entry is the conditional-**branch-selection** variant whose
  fix is a compile-time POSIX-level declaration rather than an API-exposure
  or rename patch.
