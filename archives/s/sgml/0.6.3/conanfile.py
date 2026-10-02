#!/usr/bin/env python3
"""Conan recipe for sgml 0.6.3 (sgml-common) — common SGML/XML catalogs and DTDs.

Upstream: sourceware.org docbook-tools (noarch data + shell scripts: install-catalog,
sgmlwhich). Autotools build (2001-era automake), no compiled code.

OHOS adaptation core issue: the upstream tarball ships automake helper scripts
(install-sh / mkinstalldirs / missing / INSTALL / COPYING) as *absolute symlinks*
to /usr/share/automake/*. Conan extracts them (fully_trusted filter) as dangling
links, and OHOS has no /usr/bin/install and no /usr/share/automake, so both
configure (AC_PROG_INSTALL) and `make install` would fail. Fix: rebuild
self-contained helper scripts in build() before configure (see _repair_helper_scripts).
"""
import os
import stat
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

INSTALL_SH = r"""#!/bin/sh
# Minimal POSIX 'install' replacement (self-contained OHOS fallback for the
# dangling /usr/share/automake/install-sh symlink shipped in sgml-common-0.6.3).
# Supports the subset used by this project's Makefiles: -c, -m MODE, -d, files.
mode=
dodir=0
while [ $# -gt 0 ]; do
    case "$1" in
        -c) shift ;;
        -m) mode="$2"; shift 2 ;;
        -d) dodir=1; shift ;;
        -*) echo "install-sh: unsupported option $1" >&2; exit 1 ;;
        *) break ;;
    esac
done
if [ "$dodir" = 1 ]; then
    for d in "$@"; do mkdir -p "$d" || exit 1; done
    exit 0
fi
[ $# -ge 2 ] || { echo "install-sh: missing operands" >&2; exit 1; }
# POSIX: last operand is dst; iterate the remaining operands quoted
# (no space-joined string -> no word-splitting on filenames containing
# whitespace; portable to dash/busybox ash).
eval "dst=\${$#}"
count=$#
i=0
if [ -d "$dst" ]; then
    for s in "$@"; do
        i=$(( i + 1 ))
        if [ "$i" -eq "$count" ]; then break; fi
        cp -f "$s" "$dst/" || exit 1
    done
else
    mkdir -p "$(dirname "$dst")" || exit 1
    for s in "$@"; do
        i=$(( i + 1 ))
        if [ "$i" -eq "$count" ]; then break; fi
        cp -f "$s" "$dst" || exit 1
    done
fi
[ -n "$mode" ] && chmod "$mode" "$dst"
exit 0
"""

MKINSTALLDIRS = r"""#!/bin/sh
# Minimal mkinstalldirs replacement (OHOS fallback; upstream symlink is dangling).
for d in "$@"; do mkdir -p "$d" || exit 1; done
exit 0
"""


class SgmlConan(ConanFile):
    name = "sgml"
    version = "0.6.3"
    description = "sgml-common — common SGML/XML catalogs, ISO 8879 entities and DTDs (install-catalog, sgmlwhich)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.sourceware.org/docbook-tools/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # docdir/mandir follow prefix; keep defaults (no compiled code involved)
        tc.generate()

    def _repair_helper_scripts(self):
        """Replace the tarball's dangling absolute automake symlinks with
        self-contained scripts (R33: no dependency on shell env or host automake)."""
        src = self.source_folder
        for name in ("install-sh", "mkinstalldirs", "missing", "INSTALL", "COPYING"):
            p = os.path.join(src, name)
            if os.path.islink(p) and not os.path.exists(p):
                os.unlink(p)
        for name, content in (("install-sh", INSTALL_SH), ("mkinstalldirs", MKINSTALLDIRS)):
            p = os.path.join(src, name)
            with open(p, "w") as f:
                f.write(content)
            os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def build(self):
        apply_conandata_patches(self)
        self._repair_helper_scripts()
        # Upstream is a 2001-era autotools project: doc/man/Makefile.in uses
        # 'man8_DATA = *.8' (parsed against $PWD), so out-of-source builds fail
        # (No rule to make target '*.8'). Build in-source instead.
        self.run(f"./configure --prefix={self.package_folder}", cwd=self.source_folder, env="conanbuild")
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        self.run("make install", cwd=self.source_folder, env="conanbuild")
        # drop empty platform dirs the old Makefiles create but packages don't need
        for d in ("lib", "include"):
            p = os.path.join(self.package_folder, d)
            if os.path.isdir(p) and not os.listdir(p):
                os.rmdir(p)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        # SGML data root (entities/DTDs/xml.dcl) for consumers like opensp
        self.cpp_info.resdirs = ["share/sgml"]
