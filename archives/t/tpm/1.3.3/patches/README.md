# Patches for tpm 1.3.3

**Patch count: 0**

No source patches are required for tpm 1.3.3 on OHOS.

Rationale:
- tpm is a pure POSIX shell script (`#!/bin/sh`). There is no C/C++ source to
  patch and no platform-specific code path.
- The upstream Makefile already supports `PREFIX`, `BINDIR`, `MANDIR`, and
  `DESTDIR` natively, so install-time path handling is done entirely at the
  Conan recipe layer (`package()`), with no need to modify upstream sources.
- The build-time man-page generation (`tpm.1` via `pod2man`) is skipped in the
  recipe rather than patched, because tpm's primary deliverable — the `tpm`
  command — does not depend on the man page. This is a recipe-level decision,
  not a source modification.

This directory is intentionally kept (with this note) so the archive layout
matches ARCHIVE-SPEC v3.0 and future patches can be dropped in here with a
matching `patches:` entry in `conandata.yml`.
