# Draft: libfirm 1.22.0 — Makefile version-header generation breaks on tarball builds

> Source event: `libfirm/1.22.0` HarmonyOS PC (aarch64-linux-ohos) adaptation, executor pc2-39.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

The generated `build/gen/firm_revision.h` breaks the C build:

```text
build/gen/firm_revision.h:1:1: error: expected identifier or '('
```

The file content was:

```c
\#define libfirm_VERSION_REVISION ""
```

## Root cause

Two compounding issues in the upstream Makefile:

1. `REVISION ?= $(shell git --git-dir ... describe ...)` fails when the source is
   a release tarball without `.git` (`fatal: not a git repository`), leaving
   REVISION empty.
2. The header is emitted with `REV="\#define libfirm_VERSION_REVISION \"$(REVISION)\""`.
   Inside shell double quotes `\#` stays a literal backslash, so the generated
   file starts with `\#define`, which the C preprocessor rejects.

## Recommended fix (in Makefile)

```make
REVISION ?= $(shell git --git-dir $(top_srcdir)/.git describe ... 2>/dev/null \
             || echo 2259fe4777fa51374c3f878a92b8467833e2b4f8)
# emit without the escaping backslash:
REV="$$(printf '\x23define libfirm_VERSION_REVISION "%s"\n' '$(REVISION)')"
```

## Evidence from libfirm

| State | firm_revision.h | make result |
|-------|-----------------|-------------|
| before | `\#define libfirm_VERSION_REVISION ""` | error expected identifier ( exit 2 ) |
| after  | `#define libfirm_VERSION_REVISION "2259fe47..."` | exit 0, full lib built |

## Applicability boundary

- Make-based projects synthesizing a version header from `git describe` that are
  built from tarballs (conan `get`, CI download), not only from git checkouts.
- The `\#` inside double quotes is a shell behavior — avoid emitting `#define`
  through shell strings that preserve backslashes.

## Counter-examples / limits

- Projects always built from git checkouts never hit the empty-REVISION case, but
  the `\#` escape bug still corrupts the header — worth fixing regardless.
- Do not simply delete the header or commit it: it is a generated artifact; the
  Makefile logic is the defect.

## Related knowledge

- None found in snapshot (no equivalent E-entry).