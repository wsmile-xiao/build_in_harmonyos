#!/usr/bin/env python3
"""Conan recipe — metastore 1.1.2 (store/restore filesystem metadata).

metastore is a single-binary C99 tool: it walks a file tree and writes the
owner, group, permissions, extended attributes and (optionally) mtimes of
every entry into a separate metafile, then compares or re-applies that
metadata later.  Upstream ships a hand-written "Almost Universal Makefile"
(no autotools), so build() is a single `make` invocation.

Two adaptations, both portability patches carrying no platform macro.

patches/0001 — libbsd.  metastore's sole libbsd import is strmode(3), called
once at src/metaentry.c:656 to render the mode column of the --dump output.
On OHOS that is doubly unavailable: the <bsd/string.h> header does not exist
and the symbol is undefined in musl (verified by linking probe and by nm on
the OHOS libc.so).  No libbsd package is published to the ohpcd registry, so
the dependency cannot be pulled in either.  The patch carries the BSD
implementation in-tree behind the conventional HAVE_STRMODE guard and drops
the -lbsd that no longer has anything to resolve.

patches/0002 — passwd database.  HarmonyOS has no passwd/group entry for
application uids (e.g. 20001006), so getpwuid(3)/getgrgid(3) legitimately
return NULL.  Upstream treats that as fatal for the entire metaentry
(mentry_create returns NULL), which turns save/compare/dump/apply into
no-ops for every file the process can see.  This is invisible to a local
build running as a user that does exist in /etc/passwd, and only showed up on
a real device.  The patch falls back to the numeric id and teaches the apply
path to accept that decimal form back.

patches/0003 -- extended attributes.  HMDFS rejects the POSIX
getxattr(path, attr, NULL, 0) size query with EINVAL even though
listxattr() reports the name, and upstream treats any single unreadable
attribute as fatal for the whole entry, so one bad name silently costs the
file its mode, mtime and every other attribute.  Each attribute is read
through a real buffer grown on ERANGE, and an attribute that still cannot be
read is reported and skipped rather than aborting the entry.

Upstream ships no test suite at all (the Makefile wires no `check`/`test`
target and there is no tests/ directory), so test_package/ drives the
packaged binary through its real save/compare/apply contract.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class MetastoreConan(ConanFile):
    name = "metastore"
    version = "1.1.2"
    description = (
        "Store and restore metadata (owner, group, permissions, xattrs and "
        "optionally mtime) of a filesystem tree into a separate metafile"
    )
    license = "GPL-2.0-only"
    homepage = "https://github.com/przemoc/metastore"
    url = "https://github.com/przemoc/metastore"
    topics = ("filesystem", "metadata", "xattr", "mtime", "cli", "git")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def _cross_cc(self):
        """The cross compiler from the profile, or None if unset.

        tools.build:compiler_executables is a *dict* conf, so it has to be
        read as one and indexed by role — there is no nested `:c` key.
        """
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        return compilers.get("c") if compilers else None

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"metastore not validated for {self.settings.os}"
            )
        # R33: the cross compiler must come from the profile.  Refuse to
        # build without it instead of falling back to a bare `clang`/`gcc`
        # name: a name resolved against PATH is the host compiler, so the
        # fallback would silently produce a host-architecture binary with a
        # zero exit code while every downstream claim about the target arch
        # stayed false and the build still reported success.
        if not self._cross_cc():
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables['c'] is required to build "
                "metastore; refusing to fall back to a PATH-resolved "
                "compiler (would silently build for the host)"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: the compiler comes from the Conan conf, never from a bare
        # shell env var such as ${CC} (empty on the release worker, which
        # silently falls back to the Makefile's native `gcc` default).
        # validate() already guarantees the conf is present, so there is no
        # name-based fallback here either.  Passing CC on the make command
        # line also keeps the Makefile's `ifneq ($(origin CC),environment)`
        # branch from re-prefixing it with CROSS_COMPILE.
        cc = self._cross_cc()
        self.output.info(f"metastore: building with CC={cc}")
        # -j1: the Makefile's Makefile.dep generation step is a shell loop
        # over the sources and is not parallel-safe (R9).
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        # The upstream `make install` target routes through
        # `cp -P --parents`, which lands the man page under
        # $MANDIR/man1/metastore.1 instead of $MANDIR/man1/.  Copy the
        # payload explicitly so the package layout is deterministic.
        copy(self, "metastore",
             src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        copy(self, "metastore.1",
             src=os.path.join(self.source_folder, "man1"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        for doc in ("README", "NEWS", "AUTHORS", "FILEFORMAT", "metastore.txt"):
            copy(self, doc, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "share", "doc", "metastore"),
                 keep_path=False)
        copy(self, "LICENSE.GPLv2", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
