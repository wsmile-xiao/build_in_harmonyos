#!/usr/bin/env python3
"""Conan recipe for yudit 3.1.0 — Unicode text editor for the X Window System.

OHOS (HarmonyOS PC / aarch64) port.

Upstream specifics that shape this recipe:
  * Build system is a *hand-written* autoconf variant: a generated ``configure``
    plus plain (non-automake) ``Makefile.in`` / ``Makefile.conf.in`` and one
    hand-written Makefile per sub-directory (stoolkit, swindow, swidget, addon,
    gui, mytool, uniconv, uniprint).  There is no ``make check`` target.
  * The only external library is X11 (``configure.ac:37 AC_PATH_XTRA``,
    ``configure.ac:328 X11_LIB=-lX11``); ``configure`` does not know pkg-config,
    so the X11 search paths have to be injected through CPPFLAGS/LDFLAGS.
  * ``configure`` runs the just-built ``conftest`` binaries (AC_PROG_CXX
    "whether we are cross compiling") and links every test program with the
    ambient ``LIBS``; therefore the dependency ``lib/`` directories must be on
    ``LD_LIBRARY_PATH`` during configuration, otherwise the run tests fail.
  * ``YUDIT_DATA`` is a compile-time constant derived from ``--prefix``.

OHOS port patches (see ``patches/``):
  0001-Makefile.conf.in.patch — ``make install`` uses ``install -c -s``
         (strip).  On OhOS a stripped ELF loses its signature and can no
         longer be executed at all; install the binaries without ``-s``.
  0002-configure.patch — two fixes inside ``configure``:
         (a) HMDFS: autoconf's ``umask 077 && mktemp -d ./confXXXXXX`` creates
         a 0700 directory that is *not writable* for the build user, which
         makes ``config.status`` die with "Permission denied"; lower the umask
         to 022 (knowledge base E011, ``archives/a/adns/1.6.2`` precedent).
         (b) ``configure`` probes the C++ compiler through hard-coded ``/tmp``
         paths; ``/tmp`` is a read-only erofs mount on OhOS; honour
         ``${TMPDIR:-/tmp}`` instead (knowledge base E002).
  0003-configure.ac.patch — keeps the ``${TMPDIR:-/tmp}`` fix in
         ``configure.ac`` so it survives a re-autoconf.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class YuditConan(ConanFile):
    name = "yudit"
    version = "3.1.0"
    description = ("Yudit — Unicode text editor for the X Window System; "
                   "ships the uniconv / uniprint / mytool command line tools")
    license = "GPL-2.0-only"
    homepage = "https://yudit.org/"
    url = "https://yudit.org/download/"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} is an X11 application and only supports "
                f"Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # X11 is the only forced third-party dependency of yudit
        # (configure.ac AC_PATH_XTRA / -lX11).  transitive_headers/libs so the
        # X11 headers and link libraries are visible while building yudit.
        self.requires("libx11/1.8.13", transitive_headers=True, transitive_libs=True)
        # <X11/Xlib.h> includes <X11/X.h> which lives in xorgproto.  Reached
        # only transitively, conan marks xorgproto as "Skipped binaries" and the
        # protocol headers are not installed, so require it explicitly
        # (same pattern as archives/l/libfltk/1.3.11).
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _x11_search_paths(self):
        """Collect include/lib directories of the (transitive) X11 packages."""
        includes, libdirs = [], []
        for dep in self.dependencies.host.values():
            for folder in dep.cpp_info.aggregated_components().includedirs:
                path = os.path.join(dep.package_folder, folder)
                if os.path.isdir(path) and path not in includes:
                    includes.append(path)
            for folder in dep.cpp_info.aggregated_components().libdirs:
                path = os.path.join(dep.package_folder, folder)
                if os.path.isdir(path) and path not in libdirs:
                    libdirs.append(path)
        return includes, libdirs

    def build(self):
        apply_conandata_patches(self)

        includes, libdirs = self._x11_search_paths()
        # CC / CXX / CFLAGS / CXXFLAGS / LDFLAGS come from the Conan
        # AutotoolsToolchain environment that is active for this step; only the
        # X11 search paths have to be appended.
        cppflags = " ".join(f"-I{p}" for p in includes)
        ldflags = " ".join(f"-L{p}" for p in libdirs)
        ld_library_path = ":".join(libdirs)
        old_ld_library_path = os.environ.get("LD_LIBRARY_PATH")
        if old_ld_library_path:
            ld_library_path = ld_library_path + ":" + old_ld_library_path
        os.environ["CPPFLAGS"] = " ".join(
            p for p in (os.environ.get("CPPFLAGS", ""), cppflags) if p
        ).strip()
        os.environ["LDFLAGS"] = " ".join(
            p for p in (os.environ.get("LDFLAGS", ""), ldflags) if p
        ).strip()
        os.environ["LD_LIBRARY_PATH"] = ld_library_path

        # AC_PATH_XTRA needs a single include/lib pair that actually contains
        # X11/Xlib.h and libX11.so; the remaining search paths are covered by
        # CPPFLAGS/LDFLAGS above.
        libx11 = self.dependencies["libx11"]
        libx11_info = libx11.cpp_info.aggregated_components()
        x_includes = os.path.join(libx11.package_folder, libx11_info.includedirs[0])
        x_libraries = os.path.join(libx11.package_folder, libx11_info.libdirs[0])

        configure = [
            "./configure",
            "--prefix=/",
            f"--x-includes={x_includes}",
            f"--x-libraries={x_libraries}",
        ]
        self.run(" ".join(configure), cwd=self.source_folder)
        self.run(f"make -j{build_jobs(self)}", cwd=self.source_folder)

    def package(self):
        copy(
            self,
            "COPYING.TXT",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self.run(
            f'make install DESTDIR="{self.package_folder}"', cwd=self.source_folder
        )

    def package_info(self):
        # yudit installs command line tools and data files only — there is no
        # library and no public header to consume.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
