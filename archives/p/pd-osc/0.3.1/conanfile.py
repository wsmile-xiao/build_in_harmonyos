#!/usr/bin/env python3
"""Conan recipe for pd-osc 0.3.1 (Pure Data OSC externals).

osc is the OpenSoundControl object collection for Pd, split out of the
old ``pd-mrpeach`` project.  It is built with upstream's own
``pd-lib-builder`` (``Makefile`` + ``pd-lib-builder/Makefile.pdlibbuilder``),
which yields one shared object per class:

* ``packOSC.pd_linux``    -- from ``packOSC.class.sources`` (+ OSC_timeTag.c)
* ``unpackOSC.pd_linux``  -- from ``unpackOSC.class.sources`` (+ OSC_timeTag.c)
* ``routeOSC.pd_linux``   -- derived from the bare ``class.sources``
* ``pipelist.pd_linux``   -- derived from the bare ``class.sources``

Note that ``lib.name = osc`` does **not** produce a combined ``osc.pd_linux``
library blob here: ``pd-lib-builder`` rewrites a bare ``class.sources`` into
one ``<basename>.class.sources`` per listed source file, so [routeOSC] and
[pipelist] each get their own object.  Every class is therefore loadable by
name through the canvas search path -- no ``[declare -lib osc]`` needed.

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
* The sources are plain C99 against the public ``m_pd.h`` only (no Pd
  internals such as ``m_imp.h``/``s_stuff.h``), so no patch is needed.
* Packaging trap: the same source folder also holds the unpacked pure-data
  tree under ``pd-api/``, and ``copy()`` globs recurse -- ``copy("*.pd")``
  would ship ~370 of Pd's own documentation/example patches.  ``package()``
  therefore copies the top-level files one by one (see the comment there).
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

# Upstream Makefile declares four classes; pd-lib-builder turns each source
# file into its own .pd_linux, so all four names below must show up.
EXPECTED_BLOBS = (
    "packOSC.pd_linux",
    "unpackOSC.pd_linux",
    "routeOSC.pd_linux",
    "pipelist.pd_linux",
)


class PdOscConan(ConanFile):
    name = "pd-osc"
    version = "0.3.1"
    description = "osc: OpenSoundControl object classes for Pure Data"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/pd-externals/osc"
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
                "pd-osc OHOS adaptation is validated on Linux/OHOS, not "
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
        missing = [name for name in EXPECTED_BLOBS if name not in produced]
        if missing:
            raise ConanInvalidConfiguration(
                "pd-lib-builder did not produce %s (got %s)"
                % (", ".join(missing), ", ".join(produced) or "nothing"))
        self.output.info("built %d Pd externals: %s"
                         % (len(produced), ", ".join(produced)))

    def package(self):
        ext = os.path.join(self.package_folder, "lib", "pd-externals")
        # Copy file by file instead of using ``copy(self, "*.pd*", ...)``:
        # source() also unpacks the whole pure-data tree into
        # ``<source>/pd-api/``, and conan's globbing copy recurses, which would
        # ship ~700 of Pd's own documentation/example patches into the package.
        top = self.source_folder
        installed = 0
        for name in sorted(os.listdir(top)):
            full = os.path.join(top, name)
            if not os.path.isfile(full):
                continue
            if name.endswith(".pd_linux") or name.endswith(".pd"):
                # os.listdir is non-recursive, so nothing from pd-api/ lands here
                copy(self, name, top, ext, keep_path=False)
                installed += 1
        missing = [name for name in EXPECTED_BLOBS
                   if not os.path.isfile(os.path.join(ext, name))]
        if missing:
            raise ConanInvalidConfiguration(
                "packaged externals dir lacks %s" % ", ".join(missing))
        self.output.info("packaged %d files into lib/pd-externals" % installed)
        copy(self, "README.md", top,
             os.path.join(self.package_folder, "share", "doc", "osc"),
             keep_path=False)
        copy(self, "LICENSE.txt", top,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []