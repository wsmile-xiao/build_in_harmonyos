#!/usr/bin/env python3
"""Conan recipe — triangle 1.6 (2-D quality mesh generator and Delaunay triangulator).

Triangle is Jonathan Richard Shewchuk's exact-arithmetic Delaunay
triangulator / mesh generator.  The distribution is a flat zip holding a
hand-written ``makefile``, the CLI source ``triangle.c``, the embeddable
object interface (``triangle.c`` compiled with ``-DTRILIBRARY`` +
``triangle.h``), the sample driver ``tricall.c`` and the sample PSLG
``A.poly``.

Build system : the upstream hand-written ``makefile`` (no configure, no
               CMake, no autotools).
Package form : ``bin/triangle`` (CLI, R38 -> commands.json),
               ``lib/libtriangle.a`` + ``include/triangle.h`` (embeddable API).

OHOS adaptation (patches/0001-makefile-ohos.patch) — four changes, all in the
makefile, none of them a platform stub:

  * ``-DLINUX`` is removed.  Defining it makes triangle.c
    ``#include <fpu_control.h>`` and call ``_FPU_SETCW()``
    (triangle.c:351-353, 4891-4905) — glibc/x86-only machinery that does not
    exist on the HarmonyOS worker (musl, aarch64).  aarch64 has IEEE double
    arithmetic natively, so the FPU-control-word adjustment that ``-DLINUX``
    enables is unnecessary there.
  * the X11 ``-I/usr/X11R6/include -L/usr/X11R6/lib`` switches are dropped;
    they only mattered for the optional Show Me viewer, which needs X11 and is
    not built here.
  * ``CC = cc`` becomes ``CC ?= cc`` and the switch list becomes
    ``$(CPPFLAGS) $(CFLAGS) $(CSTD)`` so the Conan toolchain's compiler and
    flags win (R33: no reliance on undefined shell variables).
  * ``CSTD = -std=gnu17`` pins the C dialect: triangle.c is 1990s K&R C with
    124 old-style function definitions, which C23 removed.  A compiler that
    defaults to ``-std=gnu23`` (e.g. GCC 15) otherwise rejects the source with
    "too many arguments to function 'readline'; expected 0, have 3".

Upstream tests: none.  Triangle ships no test suite, no ``check``/``test``
target and no CI data — the distribution has exactly one sample input,
``A.poly``.  This recipe therefore runs that sample through the built CLI in
``build()`` and drives the embeddable API from test_package; neither is
claimed as an upstream test.  See test_package/MANIFEST.yml.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class TriangleConan(ConanFile):
    name = "triangle"
    version = "1.6"
    description = ("Triangle — a two-dimensional quality mesh generator and "
                   "Delaunay triangulator (exact arithmetic)")
    license = "Triangle-non-commercial"
    homepage = "https://www.cs.cmu.edu/~quake/triangle.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Triangle's upstream makefile builds one object file and one executable —
    # there is no shared-library build (no libtool, no -fPIC) and therefore no
    # 'shared' option to declare.  static-library is the accurate type.
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "triangle 1.6 is prepared for Linux/OHOS targets only")

    def layout(self):
        basic_layout(self)

    def source(self):
        # triangle.zip is a flat archive with no top-level directory, so there
        # is nothing for strip_root to strip.
        get(self, **self.conan_data["sources"])

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # NOTE: Autotools.make() runs make in the *build* folder, not in the
        # source folder where the upstream makefile lives.  Run it in the
        # source folder; the AutotoolsToolchain environment (CC from
        # tools.build:compiler_executables, plus CPPFLAGS/CFLAGS/LDFLAGS) is
        # applied to self.run() either way.
        #
        # -j1 on purpose: this session shares the Harmony PC with a large
        # unrelated build and must not add parallel load.
        # CLI executable (triangle.c without -DTRILIBRARY)
        self.run("make -j1 triangle", cwd=self.source_folder)
        # Embeddable object file (triangle.c with -DTRILIBRARY) + tricall driver
        self.run("make -j1 trilibrary", cwd=self.source_folder)
        self._make_static_library()
        self._run_distribution_sample()

    def _make_static_library(self):
        """Wrap triangle.o into libtriangle.a for Conan consumers."""
        out = os.path.join(self.build_folder, "libtriangle.a")
        last = None
        # 'ar' is not guaranteed to be the name on PATH on the OHOS worker
        # (the SDK ships llvm-ar), so try both rather than assuming one.
        for tool in ("ar", "llvm-ar"):
            try:
                self.run('{} rcs "{}" triangle.o'.format(tool, out),
                         cwd=self.source_folder)
                if os.path.isfile(out):
                    return
            except ConanException as exc:  # tool missing: try the next name
                last = exc
        raise ConanException(
            "could not create libtriangle.a (tried ar, llvm-ar): {}".format(last))

    def _run_distribution_sample(self):
        """Run the CLI on A.poly, the only sample input the distribution ships.

        This is a smoke run over upstream's own data — not an upstream test —
        and it is what proves the exact-arithmetic code actually executes on
        the target (an object that merely links would not be caught).
        """
        workdir = os.path.join(self.build_folder, "distribution-sample")
        os.makedirs(workdir, exist_ok=True)
        copy(self, "A.poly", src=self.source_folder, dst=workdir)
        copy(self, "triangle", src=self.source_folder, dst=workdir)
        self.run("./triangle -pq A.poly", cwd=workdir)
        for suffix in (".1.node", ".1.ele", ".1.poly"):
            produced = os.path.join(workdir, "A" + suffix)
            if not os.path.isfile(produced):
                raise ConanException(
                    "triangle did not produce {} from A.poly".format("A" + suffix))

    def package(self):
        copy(self, "triangle.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "triangle", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "libtriangle.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["triangle"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
