# Draft: OHOS musl declares POSIX getline by default — legacy same-name definitions must be renamed

> Source event: blimps/3.9 path-update audit, 2026-09-05. B-2 CONFIRMED by
> Auditor + Curator; two wording findings adopted: "unconditional declaration"
> replaced by the measured default-mode vs strict-ISO behavior, and the
> cross-libc (glibc) comparison assertion removed (untested) — evidence is
> anchored on OHOS probes only.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

Legacy C code from before POSIX.1-2008 sometimes defines its own helper named
`getline`. blimps 3.9 has one in `util.c`:

```c
int getline(char *s, int n, FILE *f) { ... }   /* sole reference in the tree */
```

On OHOS this fails to compile with a hard error:

```text
error: conflicting types for 'getline'
stdio.h:155: note: previous declaration is here
ssize_t getline(char **__restrict, size_t *__restrict, FILE *__restrict);
```

## Measured facts (OHOS device, dual-mode probe)

- Default (gnu) mode: musl `stdio.h` declares `ssize_t getline(char**,
  size_t*, FILE*)` **without requiring any feature-test macro**. The legacy
  definition collides → clang hard error. This error is **not downgradable**
  with `-Wno-error` (it is not a warning).
- Strict ISO mode (`-std=c11`): the POSIX declaration is hidden — the same
  legacy definition compiles and runs (probe exit=0). This confirms the
  mechanism is purely a declaration-mode conflict, but strict-ISO compilation
  is **not** recommended as a porting fix for a whole legacy codebase.

## Recommended approach

Rename the private definition (and its call sites) out of the POSIX
namespace:

- blimps 3.9: `getline` in `util.c` is **never called anywhere** in the tree
  (the definition is the sole reference) → rename to `blimps_legacy_getline`
  is zero-risk.
- If the function is actually used and file-local, rename it and keep it
  `static` under the new name.
- If it genuinely needs getline semantics, prefer migrating callers to the
  libc `getline`/`getdelim` (char**, size_t*) interface.

## Fallbacks

1. Migrate callers to the POSIX getline/getdelim when the functionality is
   real and the POSIX interface fits.
2. Strict ISO mode (`-std=c11`) hides the declaration and makes the conflict
   disappear — use **only as a probe/diagnostic** to confirm the mechanism;
   do not flip a whole legacy project to strict ISO as the fix.

## Forbid

1. `-Wno-error=...` downgrade attempts — "conflicting types" is a hard error,
   not a warning; the flag does nothing.
2. `#define getline` macro-ization — a function-like macro with different
   arity/signature cannot coexist with the `stdio.h` declaration: it either
   leaves the declaration intact (same conflict) or rewrites it into the very
   conflict being avoided.

## Verification (self-contained, fresh shell on an OHOS device)

```bash
printf '#include <stdio.h>\nint getline(char*s,int n,FILE*f){return 0;}' \
  | /data/service/hnp/bin/clang -xc - -c 2>&1 | grep -q "conflicting types for 'getline'" \
&& printf '#include <stdio.h>\nint getline(char*s,int n,FILE*f){return 0;}' \
  | /data/service/hnp/bin/clang -xc -std=c11 - -c && echo PROBE_OK
```

Expected: default mode fails with `conflicting types for 'getline'`, strict
ISO mode compiles, `PROBE_OK` printed.

## Related knowledge

- [E093] musl missing-function genus (different mechanism: symbol truly
  absent).
- [E420], [E081] related declaration/platform-surface entries.
- Principles: P-PATCH-003 (minimal, explainable, repeatable), P-PATCH-002.
