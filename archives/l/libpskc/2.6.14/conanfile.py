#!/usr/bin/env python3
"""Conan recipe for libpskc 2.6.14 — Portable Symmetric Key Container library.

libpskc is one component of the **OATH Toolkit** distribution: it lives in the
``libpskc/`` sub-directory of ``oath-toolkit-<version>.tar.gz`` and ships its
own **pre-generated** ``configure`` (Autoconf 2.72, timestamp 2024-01-01) plus
``Makefile.in`` / ``aclocal.m4``, so it is built as a standalone autotools
project from within the unpacked source tree — no autoreconf needed.

Products: ``libpskc.so`` (+ static), ``libpskc.pc``, and the public headers
installed to ``include/pskc/`` (``pskc.h`` ``exports.h`` ``version.h``
``global.h`` ``errors.h`` ``enums.h`` ``container.h`` ``keypackage.h``).

## Dependencies (measured from ``libpskc/configure.ac``)

* **libxml2 — required**::

      PKG_CHECK_MODULES(XML2, libxml-2.0,, [AC_MSG_ERROR([Cannot find libxml2])])

  Published on ohpcd (2.15.3.x) and declared as ``pkg_config_name="libxml-2.0"``,
  which is exactly the module name configure looks up.

* **xmlsec1 — optional**::

      PKG_CHECK_MODULES(XMLSEC, xmlsec1$xmlsecengine, [xmlsec=yes], [xmlsec=no])

  With xmlsec1 absent, ``xmlsec=no`` and ``USE_XMLSEC`` stays undefined — an
  **upstream-supported** configuration. xmlsec1 is not published on ohpcd, so
  this adaptation intentionally takes that path. Consequence (documented in
  notes.md): the XML-signature entry points ``pskc_sign_x509`` /
  ``pskc_verify_x509crt`` are compiled to error-returning stubs, so the consumer
  test exercises the non-xmlsec API only.
  ``xmlcatalog`` is only consulted on the xmlsec path.

* openssl is **not** a direct dependency; it would only enter transitively via
  xmlsec1.

## OHOS adaptations

1. **``libpskc/build-aux/config.guess|config.sub`` patched for the HarmonyOS
   triplet.** Unlike pwquality's 2018-generation pair (where
   ``scripts/patch-autotools-ohos.pl`` scores 1/5), this is the **2024
   generation** and the repo script scores a full **5/5**. ``--build``/``--host``
   are deliberately not hard-coded (repo rule).

2. **``umask 077`` → ``022``** in ``libpskc/configure``. ``config.status``
   creates its temp directory in the *build* directory (not ``TMPDIR``) and
   HMDFS refuses writes into a 700 dir — the same trap documented for cracklib
   and pwquality. The configure script embeds that text for ``config.status`` to
   inherit, so widening it here fixes both.

3. ``make -j1`` (R9: parallel make trips the HMDFS jobserver fifo, E074).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps

# SUBDIRS override: build only what is needed for the library.
# libpskc/Makefile.am: SUBDIRS = gl schemas include . examples tests gtk-doc man
_BUILD_SUBDIRS = "gl schemas include ."

# libpskc/ is a *flat* autotools project: the sources (global.c, container.c,
# ...), internal.h and libpskc.map all sit directly in libpskc/ — there is no
# src/ sub-directory (measured; an earlier draft wrongly assumed src/).
_REQUIRED = (
    "libpskc.map",
    "container.c",
    "include/pskc/pskc.h",
    "include/pskc/container.h",
)


class LibpskcConan(ConanFile):
    name = "libpskc"
    version = "2.6.14"
    description = ("libpskc — Portable Symmetric Key Container (PSKC) library "
                   "(OATH Toolkit component)")
    license = "LGPL-2.1-or-later"
    homepage = "https://oath-toolkit.codeberg.page/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # libxml2 is mandatory (configure aborts with "Cannot find libxml2").
        self.requires("libxml2/2.15.3.1")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps emits the .pc files configure's PKG_CHECK_MODULES needs.
        pkg = PkgConfigDeps(self)
        pkg.generate()
        # AutotoolsDeps emits CPPFLAGS/LDFLAGS/LIBS for the dependencies.
        deps = AutotoolsDeps(self)
        deps.generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-gtk-doc",
            "--disable-gtk-doc-html",
            "--disable-gcc-warnings",
        ])
        env = tc.environment()
        # /bin/sh on this platform is toybox; configure prefers a real bash.
        env.define("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        env.define("SHELL", "/data/service/hnp/bin/bash")
        # Runtime lookup of the dependency shared libraries while configure
        # compiles and runs its test programs.
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        tc.generate(env=env)

    def _prepare_source(self):
        src = os.path.join(self.source_folder, "libpskc")
        if not os.path.isdir(src):
            raise ConanException("libpskc/ sub-directory not found in the source tree")
        for rel in _REQUIRED:
            if not os.path.isfile(os.path.join(src, rel)):
                raise ConanException(f"libpskc/{rel} missing from the source tree")
        # HMDFS: config.status writes into a 700 temp dir it creates in the
        # build directory -> Permission denied. Widen it (cracklib precedent).
        configure = os.path.join(src, "configure")
        if os.path.isfile(configure):
            with open(configure, "r", encoding="utf-8") as fh:
                text = fh.read()
            if "umask 077" in text:
                with open(configure, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(text.replace("umask 077", "umask 022"))
                self.output.info("widened umask 077 -> 022 in libpskc/configure (HMDFS)")
        return src

    def build(self):
        apply_conandata_patches(self)
        src = self._prepare_source()

        prefix = self.package_folder.replace("\\", "/")
        shared = "--enable-shared" if self.options.shared else "--disable-shared"
        static = "--disable-static" if self.options.shared else "--enable-static"
        self.run(
            f"./configure --prefix='{prefix}' {shared} {static} "
            f"--disable-gtk-doc --disable-gtk-doc-html --disable-gcc-warnings",
            cwd=src, env="conanbuild",
        )
        # NOTE: do *not* pass SUBDIRS= on the make command line. GNU make
        # exports command-line variables through MAKEFLAGS, so the override
        # also reaches the recursive sub-make inside libpskc/gl, which then
        # tries to `cd gl` again and dies with:
        #   cd: gl: No such file or directory
        # The trim therefore lives in patches/ (a change to Makefile.in's
        # SUBDIRS line), which applies the override at the right level only.
        # R9: single job (HMDFS jobserver fifo, E074).
        self.run("make -j1", cwd=src, env="conanbuild")

        self._run_upstream_tests(src)

    def _run_upstream_tests(self, src):
        """Run libpskc's own ``make check`` suite and report honestly (R51).

        ``ConanFile.run`` returns only the exit code (verified: the signature is
        ``run(...) -> int``), so pass ``stdout``/``stderr`` file objects to
        capture the suite's own output for the report.
        """
        tests = os.path.join(src, "tests")
        if not os.path.isdir(tests):
            self.output.warning("libpskc/tests not found, skipping make check")
            return
        log = os.path.join(self.build_folder, "make-check.log")
        try:
            with open(log, "w", encoding="utf-8") as fh:
                rc = self.run(f'make check SUBDIRS="tests" -j1',
                              cwd=src, env="conanbuild",
                              stdout=fh, stderr=fh, ignore_errors=True)
            tail = []
            if os.path.isfile(log):
                with open(log, "r", encoding="utf-8", errors="replace") as fh:
                    tail = [ln.rstrip() for ln in fh if ln.strip()][-4:]
            if tail:
                self.output.info(f"upstream make check: {' | '.join(tail)}")
            if rc:
                self.output.warning(
                    f"upstream make check returned {rc} for the runnable subset "
                    "— see notes.md for the per-case analysis")
        except Exception as e:
            self.output.warning(f"upstream make check could not be run: {e}")

    def package(self):
        src = os.path.join(self.source_folder, "libpskc")
        # Same caveat as build(): no SUBDIRS= on the command line, otherwise it
        # leaks into the recursive sub-make under gl/ and breaks with
        #   cd: gl: No such file or directory
        # The trimmed SUBDIRS comes from the patched Makefile.in.
        self.run("make install", cwd=src, env="conanbuild")

        libdir = os.path.join(self.package_folder, "lib")
        # libtool wrappers hard-code libdir and break consumers.
        if os.path.isdir(libdir):
            for name in os.listdir(libdir):
                if name.endswith(".la"):
                    os.remove(os.path.join(libdir, name))

        sos = [n for n in os.listdir(libdir)
               if n.startswith("libpskc.so")] if os.path.isdir(libdir) else []
        if not sos:
            raise ConanException("libpskc.so missing from the package folder")
        pc = os.path.join(libdir, "pkgconfig", "libpskc.pc")
        if not os.path.isfile(pc):
            raise ConanException(f"libpskc.pc missing at {pc}")
        if not os.path.isfile(os.path.join(self.package_folder, "include", "pskc",
                                           "pskc.h")):
            raise ConanException("include/pskc/pskc.h missing from the package folder")

    def package_info(self):
        self.cpp_info.libs = ["pskc"]
        # Headers land in include/pskc/*.h and upstream's own code uses
        # `#include <pskc/pskc.h>`, so both roots are exported (same approach as
        # the oath-toolkit recipe: include + include/libpskc).
        self.cpp_info.includedirs = ["include", "include/pskc"]
        # Upstream pkg-config name is "libpskc" (libpskc.pc: Libs: -lpskc).
        self.cpp_info.set_property("pkg_config_name", "libpskc")
