#!/usr/bin/env python3
"""Conan recipe for pd-mjlib 0.2.0 (Pure Data externals collection).

mjlib is a small collection of Pure Data externals (about, metroplus,
monorhythm, morse, n2m, pin~, prob, synapseA~).  It is built with upstream's
own ``pd-lib-builder`` (``Makefile.pdlibbuilder``), which produces one
``<class>.pd_linux`` shared object per class -- the objects are then found by
Pd at patch-load time through the canvas search path.

OHOS notes
----------
* The ``puredata`` Conan package is an *application*: it installs ``pd`` and
  its data dir but **not** the Pd API headers (``m_pd.h``).  This recipe
  therefore fetches the matching upstream Pure Data source tree (0.54-1, the
  same release ``puredata/0.54.1`` is built from) and points
  ``PDINCLUDEDIR`` at its ``src`` directory.
* ``pd-lib-builder`` detects the target OS from ``$(CC) -dumpmachine``; the
  OHOS clang reports ``aarch64-...-linux-ohos`` so it selects the Linux flags
  and the ``pd_linux`` extension.  ``CC`` is passed explicitly from the
  compiler-executables conf.
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

# Pure Data source release the puredata/0.54.1 package is built from; used
# only to obtain the Pd API headers (m_pd.h and friends).
PD_SRC_URL = "https://codeload.github.com/pure-data/pure-data/tar.gz/refs/tags/0.54-1"
PD_SRC_SHA256 = "19a0e2bfcbb5bad5e6dd016d1cda35464db6de008d1803a14c7e1f1625f31353"

MIN_CLASSES = 8


class PdMjlibConan(ConanFile):
    name = "pd-mjlib"
    version = "0.2.0"
    description = "mjlib: a collection of Pure Data externals"
    license = "GPL-2.0-or-later"
    homepage = "https://puredata.info"
    url = ""

    # The package installs Pd external shared objects (lib/pd-externals/*.pd_linux),
    # not command-line programs, so it is a library, not an application.  Declaring
    # it as an application made the R38 gate demand a CLI commands.json.
    package_type = "library"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pd-mjlib OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        pd_dir = os.path.join(self.source_folder, "pd-api")
        os.makedirs(pd_dir, exist_ok=True)
        get(self, url=PD_SRC_URL, sha256=PD_SRC_SHA256,
            filename="pure-data-0.54-1.tar.gz", strip_root=True,
            destination=pd_dir)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler("c", "clang")
        pdinc = os.path.join(self.source_folder, "pd-api", "src")
        if not os.path.isfile(os.path.join(pdinc, "m_pd.h")):
            raise ConanInvalidConfiguration(
                "Pd API header not found: " + os.path.join(pdinc, "m_pd.h"))
        self.run('make -j1 CC="%s" PDINCLUDEDIR="%s"' % (cc, pdinc),
                 cwd=self.source_folder, env="conanbuild")
        produced = sorted(f for f in os.listdir(self.source_folder)
                          if f.endswith(".pd_linux"))
        if len(produced) < MIN_CLASSES:
            raise ConanInvalidConfiguration(
                "expected at least %d externals, produced %d"
                % (MIN_CLASSES, len(produced)))
        self.output.info("built %d Pd externals" % len(produced))

    def package(self):
        ext = os.path.join(self.package_folder, "lib", "pd-externals")
        copy(self, "*.pd_linux", self.source_folder, ext)
        copy(self, "help/*.pd", self.source_folder, ext)
        copy(self, "mjlib-meta.pd", self.source_folder, ext)
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
