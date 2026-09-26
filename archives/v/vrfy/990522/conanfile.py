#!/usr/bin/env python3
"""Conan recipe for vrfy 990522 - SMTP address verification tool.

``vrfy`` verifies e-mail addresses by connecting to the SMTP server of the
target domain (VRFY/EXPN, DNS MX lookup) and by syntactic checks.  It is a
small 1998 C program built by a hand-written Makefile.

OHOS notes
----------
* Plain Makefile.  ``CC`` is injected from the Conan build environment and the
  resolver libraries are not linked (the Makefile defaults to ``-lresolv``,
  which OHOS does not ship; bionic provides the resolver entry points in libc).
* The sources are old K&R-style C; compiled as ``gnu89`` so clang 15 accepts
  implicit declarations and old-style definitions.
* The build environment has no ``install(1)``, so ``package()`` copies the
  binary and manual page manually.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, save
from conan.tools.files import apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# OHOS bionic provides res_search()/dn_expand()/dn_skipname() and the
# <resolv.h> interface, but it does not export the BIND resolver state `_res`
# nor the BIND-internal DNS packet helper `_getshort` that mxrr.c uses.
_COMPAT_C = """\
#include <resolv.h>

/* vrfy sets `_res.options` to RES_DEFNAMES/RES_DEBUG; bionic's resolver does
 * not export `_res`, so provide one (the flags are advisory on OHOS). */
struct __res_state _res;

/* BIND-internal 16-bit big-endian DNS packet reader (glibc/libresolv only). */
unsigned short
_getshort(const unsigned char *cp)
{
    return (unsigned short)((cp[0] << 8) | cp[1]);
}
"""


class VrfyConan(ConanFile):
    name = "vrfy"
    version = "990522"
    description = "Verify e-mail addresses via SMTP VRFY/EXPN and DNS"
    license = "BSD-3-Clause"
    homepage = "https://packages.debian.org/vrfy"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "vrfy OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler("c", "clang")
        # Provide the BIND symbols bionic lacks (see _COMPAT_C).
        save(self, os.path.join(self.source_folder, "ohos_compat.c"), _COMPAT_C)
        objs = ("main.o pars.o smtp.o conn.o stat.o mxrr.o util.o vers.o "
                "ohos_compat.o")
        # RES/LIBS override the Makefile's -lresolv/-lsocket/-lnsl defaults;
        # the OHOS libc provides the resolver/getnet entry points.
        # -DSYSV_STRCHR makes port.h alias rindex -> strrchr (BSD name absent
        # from bionic); gnu89 + relaxed warnings accept the 1998 K&R sources.
        cflags = ("-O -std=gnu89 -DSYSV_STRCHR -Wno-implicit-function-declaration "
                  "-Wno-implicit-int -Wno-int-conversion -Wno-return-type "
                  "-Wno-deprecated-non-prototype")
        self.run('make CC="{}" RES= LIBS= OBJS="{}" CFLAGS="{}"'.format(
            cc, objs, cflags), cwd=self.source_folder)

    def package(self):
        copy(self, "vrfy",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "vrfy.1",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
