# E336 - Include the dependency header that owns the API declaration

> Contributor: xuguowei | Status: DRAFT | Created: 2026-08-22

## Scope

Use this pattern when a legacy C translation unit calls a dependency API but
does not include the public header that declares it. It is especially relevant
after upgrading a dependency whose broad or neighboring headers no longer
expose declarations transitively.

This draft does not cover missing Conan include directories, missing generated
headers in a package, or APIs that the target libc does not implement.

## Symptom

The dependency include directory is already present, so adding more `-I` paths
does not change the failure. A C89 or `-ansi` build instead treats the
undeclared function as returning `int`, and modern Clang reports pointer type
failures at the call sites:

```text
wvSummary.c:104:17: error: incompatible integer to pointer conversion
  initializing 'const GValue *' with an expression of type 'int'
wvSummary.c:146:21: error: incompatible integer to pointer conversion
  initializing 'GsfDocMetaData *' with an expression of type 'int'
```

Related warnings can compare the implicit integer result with `NULL` or pass it
to a `%s` format expecting a pointer.

## Root cause

`wvSummary.c` used `gsf_doc_prop_get_val()`, `gsf_doc_prop_get_link()`, and
`gsf_doc_meta_data_new()` while including nearby libgsf headers but not
`<gsf/gsf-doc-meta-data.h>`, which owns those declarations in libgsf 1.14.58.

The include search path and linked library were already correct. The failure
was a source-level declaration-ownership defect exposed by the newer dependency
header layout and Clang's pointer conversion checks.

## Recommended solution

1. Search the installed dependency headers for the failing API declaration.
2. Add that owning public header directly to the translation unit.
3. Keep compiler diagnostics enabled; do not add a handwritten prototype.
4. Rebuild with the same source archive, dependency revisions, and toolchain.
5. Confirm the previously failing object compiles and the build advances to a
   later, independent stage.

For wv 1.2.9 the source patch is one line:

```c
#include <gsf/gsf-doc-meta-data.h>
```

## Before/after evidence

Both runs used wv 1.2.9, the same source SHA256, libgsf 1.14.58, and the OHOS
Clang 15 toolchain.

| Run | Relevant source state | Result |
|---|---|---|
| shadow r11 | no direct metadata header | `wvSummary.o` failed with two implicit-int pointer conversions |
| shadow r13 | one direct metadata header added | `wvSummary.o` compiled, `wvSummary` linked, package creation completed |

r13 later failed in the independent `test_package` stage because CMake was not
discoverable. That later failure is useful evidence that the header repair
removed the original compilation blocker without suppressing it. Shadow r18
subsequently passed Conan create and all three public API assertions.

## Duplicate boundary

- E081 and E093 cover target libc APIs that are genuinely unavailable. Here the
  libgsf APIs exist and are linked; only their owning header was omitted.
- E309 covers generated public headers omitted from a package. Here
  `gsf-doc-meta-data.h` is installed and discoverable.
- `DRAFT-conan-staticlib-transitive-headers` covers Conan traits that fail to
  propagate dependency include directories. Here the correct libgsf include
  directory was already on the compile command.
- E307 covers test packages that cannot start CMake. That was the next r13
  blocker, not the `wvSummary.c` root cause.

## Forbidden shortcuts

- Do not suppress implicit-function or integer-to-pointer diagnostics.
- Do not copy dependency function prototypes into the consumer source.
- Do not add a global forced include for one translation unit's omission.
- Do not claim an API is absent until the installed public headers are checked.

## Validation boundary

The final wv consumer test validates three public initialization APIs. It does
not parse a complete Word document, and this draft does not claim that level of
functional coverage. Final Path B recognition remains a reviewer decision.
