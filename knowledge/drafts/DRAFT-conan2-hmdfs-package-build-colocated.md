# DRAFT-conan2-hmdfs-package-build-colocated - Conan 2.x package/build share a parent dir

> **Contributor**: AtomCode (GLM-5.2) | **Status**: DRAFT | **Updated**: 2026-09-22
> **Severity**: high | **Category**: conan / hmdfs / cache

## Problem

On the device, qtbase + qtnetworkauth compile products filled the disk. Trying to
free space with `rm -rf <conan-home>/p/b/*/` removed not only the build folder but
also the **package folder**, because Conan 2.x lays them out as siblings:

```
conan-home/p/b/<hash>/
  b/   # build
  p/   # package (conaninfo.txt, lib, include, ...)
```

`cache.sqlite3` still recorded the package at the deleted path, so the next
`conan create` failed at install time:

```
qtbase/6.11.1: Already installed! (1 of 1)
ERROR: os.utime(package_layout.base_folder, None)
FileNotFoundError: [Errno 2] No such file or directory
```

`conan list "qtbase/*:*"` also reported a `Corrupted package ... without
conaninfo.txt`.

## Implementation

- Free space safely with `conan remove "<name>/<ver>" -c`, which deletes the
  recipe, binaries and the sqlite rows together.
- If only the build tree must go, delete the build child `p/b/<hash>/b/` only —
  never the whole `p/b/<hash>/`.
- A `conan cache clean "*/*" --all` with the `*/*` pattern mis-parsed and walked
  `$HOME`; avoid that pattern.

## Verification boundary

After `conan remove "qtbase/6.11.1" -c`, a fresh `conan create` of qtbase 6.11.1
and qtnetworkauth 6.11.1 succeeded (2/2 upstream tests + consumer test passed).

## Source

- Package: `archives/q/qtnetworkauth/6.11.1` shadow CI cleanup
- PR: pending (issue 待补)
