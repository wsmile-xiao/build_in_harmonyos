#!/usr/bin/env python3
"""Conan recipe for pd-smlib 0.13.0 (Pure Data externals: DSP data -> controls).

SMLib (IOhannes m zmölnig) is a collection of 40 Pure Data external classes for
control-rate vector/stream processing (vmax, vsum, vmtof, vclip, vstd, ...).
It is built with the ``pd-lib-builder`` makefile bundled in the release tarball
(``pd-lib-builder/Makefile.pdlibbuilder``), which emits one ``<class>.pd_linux``
shared object per class; Pd then finds them by class name through the canvas
search path.

OHOS notes
----------
* The published ``puredata/0.54.1`` package is an *application*: it installs the
  ``pd`` executable and its data directory but **not** the Pd API headers
  (``m_pd.h``).  This recipe therefore fetches the matching upstream Pure Data
  source tree (0.54-1, the very release ``puredata/0.54.1`` is built from) in
  ``source()`` and points ``PDINCLUDEDIR`` at its ``src`` directory.
* ``pd-lib-builder`` chooses its target branch from ``$(CC) -dumpmachine``; the
  OHOS clang reports ``aarch64-...-linux-ohos``, so the Linux flags and the
  ``pd_linux`` extension are selected -- which is exactly what Pd on OHOS
  expects.  ``CC`` is passed explicitly from the profile's
  ``tools.build:compiler_executables`` conf (never from a bare ``${CC}``).
* Pure C (``m_pd.h`` + ``math.h``), no third-party dependency, no patch needed:
  the 40 classes compile unmodified for OHOS aarch64.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout

# Pure Data release that puredata/0.54.1 is built from; used only to obtain the
# Pd API headers (m_pd.h and friends) that the puredata package does not ship.
PD_SRC_URL = "https://codeload.github.com/pure-data/pure-data/tar.gz/refs/tags/0.54-1"
PD_SRC_SHA256 = "19a0e2bfcbb5bad5e6dd016d1cda35464db6de008d1803a14c7e1f1625f31353"

# The upstream Makefile declares exactly 40 classes (<class>.class.sources).
MIN_EXTERNALS = 40

EXTERNALS_DIR = os.path.join("lib", "pd-externals")


class PdSmlibConan(ConanFile):
    name = "pd-smlib"
    version = "0.13.0"
    description = "SMLib: Pure Data externals for mapping DSP data to controls"
    license = "GPL-2.0-or-later"
    homepage = "https://puredata.info"
    url = ""

    # Installs Pd external shared objects (lib/pd-externals/*.pd_linux), not
    # command line programs -> a shared library, so no CLI commands.json is
    # required.
    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pd-smlib is validated on Linux/OHOS, not " + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        apply_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        pd_api = os.path.join(self.source_folder, "pd-api")
        os.makedirs(pd_api, exist_ok=True)
        get(self, url=PD_SRC_URL, sha256=PD_SRC_SHA256,
            filename="pure-data-0.54-1.tar.gz", strip_root=True,
            destination=pd_api)

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
        if len(produced) < MIN_EXTERNALS:
            raise ConanInvalidConfiguration(
                "expected at least %d Pd externals, produced %d"
                % (MIN_EXTERNALS, len(produced)))
        self.output.info("built %d Pd externals (SMLib)" % len(produced))

    def package(self):
        ext = os.path.join(self.package_folder, EXTERNALS_DIR)
        copy(self, "*.pd_linux", self.source_folder, ext)
        # datafiles of the upstream Makefile + the extradirs examples/
        copy(self, "*-help.pd", os.path.join(self.source_folder, "help"), ext)
        copy(self, "SMLib.pd", self.source_folder, ext)
        copy(self, "smlib-meta.pd", self.source_folder, ext)
        copy(self, "README.txt", self.source_folder, ext)
        copy(self, "*.pd", os.path.join(self.source_folder, "examples"),
             os.path.join(ext, "examples"))
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Pd finds its externals through the canvas search path (lib/pd-externals),
        # not through link-time dependencies, so no cpp_info entries are exposed.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
