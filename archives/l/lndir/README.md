# lndir

X.Org `lndir` — create a shadow directory of symbolic links to another directory tree.

## Description

`lndir` creates a shadow directory tree (the "to" directory) consisting of
symbolic links pointing at the contents of a source directory tree (the
"from" directory). Directories are created (recursively), regular files become
symlinks, and revision-control metadata directories (`.git`, `.hg`, `.svn`,
`CVS`, `RCS`, `SCCS`, `BitKeeper`, `CVS.adm`) are skipped unless `-withrevinfo`
is given.

Typical usage:

```sh
mkdir /usr/local/src/new-X
cd /usr/local/src/new-X
lndir ../X
```

## Upstream

- Homepage: https://gitlab.freedesktop.org/xorg/util/lndir
- Release tarball: https://xorg.freedesktop.org/archive/individual/util/lndir-1.0.5.tar.xz
- License: MIT-open-group (Open Group X11 license)

## Build system

Autotools (`configure` + `make`). The published release tarball ships a
pre-generated `configure` and `Makefile.in`, so `autoreconf` is not required.

The only build dependency is `xorgproto` (provides the `xproto` pkg-config
module and the `X11/Xos.h`, `X11/Xfuncproto.h` headers). No libraries are
linked (`XPROTO_LIBS` is empty).

## Upstream tests

There are **no upstream tests**. `Makefile.am` declares only
`bin_PROGRAMS = lndir` — no `TESTS`, no `check_PROGRAMS`, no `check-local`
target. The automake `check` target is the default no-op (`check-am: all-am`).

The project's `test_package/` builds a small source directory tree, runs the
newly built `lndir` binary against it, and verifies that the resulting shadow
tree contains the expected symlinks and subdirectories.

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 1.0.5   | built  | X.Org stable release; upstream has no test suite |
