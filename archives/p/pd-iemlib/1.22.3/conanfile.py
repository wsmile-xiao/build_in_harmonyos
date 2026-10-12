#!/usr/bin/env python3
"""Conan recipe for pd-iemlib 1.22.3 (Pure Data externals collection).

iemlib is Thomas Musil's (IEM / KUG Graz) collection of Pure Data externals:
unit converters ([db2v]/[v2db]/[wrap]/[f2note]), recursive filters
([prvu~]/[rvu~]/[pvu~]), t3_lib ([t3_bpe]/[t3_delay]/[t3_line~]/[t3_metro]),
plus 165 abstractions and 77 help patches.

Upstream builds it with its own ``pd-lib-builder`` (``Makefile.pdlibbuilder``)
and ``make-lib-executable=yes``, so the whole collection ends up in ONE
multi-object shared object ``iemlib.pd_linux`` instead of one ``.pd_linux``
per class.  Pd finds it through its ``<libname>_setup`` entry point when the
patch (or the startup path) references the library, hence the ``[iemlib]``
object in the consumer test.

OHOS notes
----------
* The ``puredata`` Conan package is an *application*: it installs ``pd`` and
  its data dir but **not** the Pd API headers (``m_pd.h``, ``g_canvas.h``).
  This recipe therefore fetches the matching upstream Pure Data source tree
  (0.54-1, the same release ``puredata/0.54.1`` is built from) and points
  ``PDINCLUDEDIR`` at its ``src`` directory.  iemlib's Makefile passes
  ``-DHAVE_G_CANVAS_H=1``, and ``g_canvas.h`` lives in that same ``src`` dir.
* ``pd-lib-builder`` detects the target OS from ``$(CC) -dumpmachine``; the
  OHOS clang reports ``aarch64-...-linux-ohos`` so it selects the Linux flags
  and the ``pd_linux`` extension.  ``CC`` is passed explicitly from the
  compiler-executables conf.
* No source patch is needed: the tree is plain C99 against the public
  ``m_pd.h`` only, no Pd internals (``m_imp.h``/``s_stuff.h``), no autotools.
* Externals deliberately do **not** link ``libpd``: the Pd API symbols stay
  undefined in ``iemlib.pd_linux`` and are resolved from the running ``pd``
  process at load time (``readelf -d`` shows ``NEEDED`` = ``libc.so`` only).
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

# The library is a single shared object; refuse to ship an empty/stub one.
MIN_LIBRARY_BYTES = 100000
# Upstream ships 77 help patches and 299 abstraction files (165 abstractions
# + 134 of their help patches). Thresholds keep a truncated data install from
# passing silently.
MIN_HELP_PATCHES = 70
MIN_ABSTRACTIONS = 150


class PdIemlibConan(ConanFile):
    name = "pd-iemlib"
    version = "1.22.3"
    description = "iemlib: Pure Data externals by Thomas Musil (IEM/KUG Graz)"
    license = "LGPL-2.1-or-later"
    homepage = "https://git.iem.at/pd/iemlib"
    url = ""

    # The package installs a Pd external shared object (lib/pd-externals/
    # iemlib.pd_linux), not command-line programs, so it is a library.
    # Declaring it as an application would make the R38 gate demand a CLI
    # commands.json.
    package_type = "library"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pd-iemlib OHOS adaptation is validated on Linux/OHOS, not "
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
        for header in ("m_pd.h", "g_canvas.h"):
            if not os.path.isfile(os.path.join(pdinc, header)):
                raise ConanInvalidConfiguration(
                    "Pd API header not found: " + os.path.join(pdinc, header))
        self.run('make -j1 CC="%s" PDINCLUDEDIR="%s"' % (cc, pdinc),
                 cwd=self.source_folder, env="conanbuild")

        library = os.path.join(self.source_folder, "iemlib.pd_linux")
        if not os.path.isfile(library):
            raise ConanInvalidConfiguration(
                "pd-lib-builder produced no iemlib.pd_linux")
        size = os.path.getsize(library)
        if size < MIN_LIBRARY_BYTES:
            raise ConanInvalidConfiguration(
                "iemlib.pd_linux is only %d bytes (expected >= %d); the "
                "multi-object library looks truncated" % (size, MIN_LIBRARY_BYTES))
        self.output.info("built iemlib.pd_linux (%d bytes)" % size)

    def _count(self, subdir, suffix):
        d = os.path.join(self.source_folder, subdir)
        if not os.path.isdir(d):
            return 0
        return len([f for f in os.listdir(d) if f.endswith(suffix)])

    def package(self):
        ext = os.path.join(self.package_folder, "lib", "pd-externals")
        copy(self, "iemlib.pd_linux", self.source_folder, ext)
        copy(self, "*.pd", self.source_folder, ext)
        copy(self, "*.txt", self.source_folder, ext)
        copy(self, "*", os.path.join(self.source_folder, "help"), ext)
        copy(self, "*", os.path.join(self.source_folder, "abs"), ext)
        # alias/ mixes .pd aliases with .c snippet files; only the .pd ones
        # are loadable at run time.
        copy(self, "*.pd", os.path.join(self.source_folder, "alias"), ext)
        copy(self, "*", os.path.join(self.source_folder, "examples"), ext)

        helps = self._count("help", ".pd")
        abstractions = self._count("abs", ".pd")
        if helps < MIN_HELP_PATCHES:
            raise ConanInvalidConfiguration(
                "expected at least %d help patches, found %d"
                % (MIN_HELP_PATCHES, helps))
        if abstractions < MIN_ABSTRACTIONS:
            raise ConanInvalidConfiguration(
                "expected at least %d abstractions, found %d"
                % (MIN_ABSTRACTIONS, abstractions))
        self.output.info("packaged %d help patches, %d abstractions"
                         % (helps, abstractions))
        copy(self, "LICENCE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "GnuLGPL.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
