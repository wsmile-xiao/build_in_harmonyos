#!/usr/bin/env python3
"""Conan recipe for pd-ggee 0.28 (Pure Data externals -- "ggee").

ggee is Guenter Geiger's Pure Data library: control objects, experimental
synths, filters, GUI objects and signal objects.  It is built with upstream's
own ``pd-lib-builder`` (``Makefile.pdlibbuilder``), which produces one
``<class>.pd_linux`` shared object per class -- Pd then dlopen()s them by class
name at patch-load time.

OHOS notes
----------
* ``pd-lib-builder`` (v0.6.0, bundled in the tarball) derives its platform from
  ``$(CC) -dumpmachine``, not from ``uname``.  Both the OHOS NDK clang on the CI
  worker and the local WSL cross shim report an ``aarch64-...-linux-ohos``
  triplet, so the ``linux`` word matches and the Linux branch is taken
  (``.pd_linux`` extension, ``-DUNIX``, ``-fPIC -shared -rdynamic``,
  ``-lc -lm``).  ``system=Linux`` is still passed explicitly so the platform
  choice does not depend on the exact triplet spelling of the worker's clang.
* ``arch.c.flags`` resolves to ``-mcpu=cortex-a53`` because the first triplet
  word is ``aarch64``; that is accepted verbatim by the OHOS clang.
* ``PDINCLUDEDIR`` is pointed at the ``puredata/0.54.1`` package: it is declared
  an *application*, so it exports no ``includedirs``, but the Pd API headers
  (``m_pd.h`` and ``g_canvas.h``) are installed under ``include/pd/``.  ggee's
  sources only ever include the public Pd API (``<m_pd.h>`` plus the
  ``g_canvas.h`` shipped alongside it), never Pd internals such as ``m_imp.h``.
* No patch is required: upstream sources build unmodified for OHOS aarch64.
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

# Number of entries in upstream Makefile's `class.sources` (42).  `gui/fatom.c`
# is commented out upstream, so the [fatom] class itself is deliberately not
# built; `fatom.h` is still #included by gui/slider.c, gui/sliderh.c and
# gui/ticker.c, which use only its declarations and inline helpers and pull in
# no undefined fatom* symbol (verified with nm -D --undefined-only).
EXPECTED_EXTERNALS = 42

# Runtime data files declared by upstream Makefile's `datafiles`, on top of the
# per-class *-help.pd patches.  All of them are installed FLAT into the same
# directory: pd-lib-builder v0.6.0's install-datafiles rule is a per-file
# `install -p -m 644` into one installpath (no `cp -R`), so flat is exactly what
# upstream `make install` produces -- and Pd resolves help patches by
# "<declared path>/<class>-help.pd" without recursing into subdirectories.
DATA_FILES = ("ggee-meta.pd",)
GUI_DATA_FILES = ("state.list", "logo100.gif")
LICENSE_FILES = ("LICENSE.txt", "README.txt")


class PdGgeeConan(ConanFile):
    name = "pd-ggee"
    version = "0.28"
    description = "ggee: Pure Data externals by Guenter Geiger (control, experimental, filters, gui, signal)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/pd-externals/ggee"
    url = ""

    # The package installs Pd external shared objects (lib/pd-externals/*.pd_linux)
    # plus help patches -- no command-line program is installed, so it is a
    # library and needs no software-level commands.json (R38).
    package_type = "library"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: OHOS counts as a Linux-like target for this recipe.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pd-ggee OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "pd-ggee is a set of Pd externals that Pd dlopen()s; "
                "pd-lib-builder has no static mode")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Supplies the Pd API headers (m_pd.h / g_canvas.h) the externals
        # compile against.  Already published to the artifact repository.
        self.requires("puredata/0.54.1")

    def export_sources(self):
        export_conandata_patches(self)

    def _pd_include_dir(self):
        """Directory holding m_pd.h inside the puredata package folder.

        puredata/0.54.1 is an application package and therefore publishes no
        cpp_info.includedirs, but the headers are installed regardless.
        """
        dep = self.dependencies["puredata"]
        for candidate in (os.path.join(dep.package_folder, "include", "pd"),
                          os.path.join(dep.package_folder, "include")):
            if os.path.isfile(os.path.join(candidate, "m_pd.h")):
                return candidate
        raise ConanInvalidConfiguration(
            "puredata/0.54.1 does not provide m_pd.h (looked in %s/include[/pd])"
            % dep.package_folder)

    def _compiler(self):
        # R33: never rely on an undefined shell variable -- take the compiler
        # from the Conan profile conf that both W3 and CI set.
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict) or {}
        return executables.get("c") or "clang"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        pdinc = self._pd_include_dir()
        if not os.path.isfile(os.path.join(pdinc, "g_canvas.h")):
            raise ConanInvalidConfiguration(
                "Pd API header not found: " + os.path.join(pdinc, "g_canvas.h"))
        self.run('make -j1 system=Linux CC="%s" PDINCLUDEDIR="%s"'
                 % (self._compiler(), pdinc),
                 cwd=self.source_folder, env="conanbuild")
        produced = sorted(f for f in os.listdir(self.source_folder)
                          if f.endswith(".pd_linux"))
        if len(produced) != EXPECTED_EXTERNALS:
            raise ConanInvalidConfiguration(
                "expected %d Pd externals (upstream Makefile class.sources), "
                "produced %d: %s"
                % (EXPECTED_EXTERNALS, len(produced), ", ".join(produced)))
        self.output.info("built %d Pd externals" % len(produced))

    def package(self):
        ext = os.path.join(self.package_folder, "lib", "pd-externals")
        licenses = os.path.join(self.package_folder, "licenses")
        copy(self, "*.pd_linux", self.source_folder, ext)
        # 45 help patches live in per-class subdirectories upstream; flatten them
        # next to the externals, matching upstream install-datafiles and Pd's
        # non-recursive help lookup.
        copy(self, "*-help.pd", self.source_folder, ext, keep_path=False)
        for name in DATA_FILES:
            copy(self, name, self.source_folder, ext, keep_path=False)
        for name in GUI_DATA_FILES:
            copy(self, name, os.path.join(self.source_folder, "gui"), ext)
        for name in LICENSE_FILES:
            copy(self, name, self.source_folder, licenses, keep_path=False)

    def package_info(self):
        # The externals are dlopen()ed by Pd by path, they are not linked
        # against, so this package exports no libs/includes/bins of its own.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
