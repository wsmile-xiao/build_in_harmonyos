# paxrelabel

> Package-level PaX flag management tool.

## Introduction

`paxrelabel` loads PaX exception rule files from configured directories and
applies the requested `user.pax.flags` extended attribute to matching binaries.
It is a small C command-line utility maintained in the Alpine GitLab namespace.

## OHOS adaptation notes

- Build system: raw Makefile.
- Dependencies: none.
- The package installs the `paxrelabel` executable into Conan `bin/`.
- A portability patch avoids non-portable `strlcpy`/`alloca` usage and keeps the
  default upstream search path unchanged while allowing tests to override it via
  `PAXRELABEL_SEARCH_PATH`.

## Verification

The upstream release contains no bundled test suite. The Conan
`test_package` runs deterministic command-line checks against the packaged
binary, including a valid no-op rule path and an invalid-flag fault-injection
case.

## References

- Upstream repository: https://gitlab.alpinelinux.org/ariadne/paxrelabel
- Source archive: https://distfiles.alpinelinux.org/distfiles/v3.23/paxrelabel-v0.1.1.tar.gz

