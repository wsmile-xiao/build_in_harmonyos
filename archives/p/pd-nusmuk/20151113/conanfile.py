#!/usr/bin/env python3
"""Conan recipe for pd-nusmuk 20151113 (Pure Data externals collection).

pd-nusmuk is Cyrille Henry's collection of Pure Data externals and
abstractions.  Upstream ships it as two libraries built by the *old* Pd
``Makefile`` template: ``nusmuk-utils`` (13 externals) and ``nusmuk-audio``
(4 externals).

OHOS notes
----------
* Both subdirectories use the old Pd ``Makefile`` template (1.0.5 / 1.0.14)
  rather than ``pd-lib-builder``.  The template picks its target from
  ``$(uname -s)``.  On OHOS CI workers ``uname -s`` returns
  ``HarmonyOS`` (not ``Linux``), so the template's Linux branch — which sets
  ``EXTENSION=pd_linux`` and adds ``-fPIC``/``-shared`` — never fires.
  Passing ``UNAME=Linux`` on the make command line forces the Linux branch
  and makes the build work on both local and CI (no source patch needed).
* The template hardcodes ``PD_INCLUDE = $(PD_PATH)/include`` with
  ``PD_PATH = /usr`` on Linux.  ``PD_INCLUDE`` is overridden on the make
  command line and pointed at the Pd API headers of the matching pure-data
  release; a command-line assignment beats the ``=`` in the Makefile, so no
  patch is needed.
* ``tabosc4c~.c`` / ``tabosci~.c`` include ``<machine/endian.h>``, but only
  under ``__FreeBSD__``/``__APPLE__``; the ``__linux__`` branch uses musl's
  ``<endian.h>``, which defines ``BYTE_ORDER``/``LITTLE_ENDIAN``.  The OHOS
  clang reports ``aarch64-linux-ohos`` and defines ``__linux__``/``__unix__``,
  so the endianness block compiles as-is.
* The ``puredata`` Conan package is an application and does **not** install
  ``m_pd.h``.  Like ``pd-maxlib``/``pd-mjlib`` this recipe fetches the
  ``pure-data 0.54-1`` source tree (the release ``puredata/0.54.1`` is built
  from) purely to obtain the headers.
* ``make install`` is deliberately not used: its Linux branch pipes every
  external through ``strip``, and the ``strip`` found on x86 builders cannot
  recognise aarch64 ELF, which would break the build on half the workers.
  The externals and their Pd assets are copied into the package instead.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# Pure Data source release that puredata/0.54.1 is built from; used only to
# obtain the Pd API headers (m_pd.h and friends).
PD_SRC_URL = "https://codeload.github.com/pure-data/pure-data/tar.gz/refs/tags/0.54-1"
PD_SRC_SHA256 = "19a0e2bfcbb5bad5e6dd016d1cda35464db6de008d1803a14c7e1f1625f31353"

# upstream library directory -> number of .c sources listed in its Makefile
LIBRARIES = {"utils": 13, "audio": 4}


class PdNusmukConan(ConanFile):
    name = "pd-nusmuk"
    version = "20151113"
    description = "pd-nusmuk: Cyrille Henry's collection of Pure Data externals"
    license = "GPL-2.0-only"
    homepage = "https://puredata.info"
    url = ""

    # The package installs Pd external shared objects (lib/pd-externals/*/
    # *.pd_linux) and the matching Pd patches, not command-line programs, so
    # it is a library.  Declaring it an application would make the R38 gate
    # demand a CLI commands.json.
    package_type = "library"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pd-nusmuk OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

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
        cc = self._compiler("c", "clang")
        pdinc = os.path.join(self.source_folder, "pd-api", "src")
        if not os.path.isfile(os.path.join(pdinc, "m_pd.h")):
            raise ConanInvalidConfiguration(
                "Pd API header not found: " + os.path.join(pdinc, "m_pd.h"))

        total = 0
        for lib, expected in LIBRARIES.items():
            work = os.path.join(self.source_folder, lib)
            self.run('make -j1 UNAME=Linux CC="%s" PD_INCLUDE="%s" all' % (cc, pdinc),
                     cwd=work, env="conanbuild")
            produced = sorted(f for f in os.listdir(work)
                              if f.endswith(".pd_linux"))
            if len(produced) != expected:
                raise ConanInvalidConfiguration(
                    "nusmuk-%s: expected %d externals, produced %d"
                    % (lib, expected, len(produced)))
            total += len(produced)
        self.output.info("built %d Pd externals" % total)

    def package(self):
        ext_root = os.path.join(self.package_folder, "lib", "pd-externals")
        for lib in LIBRARIES:
            src = os.path.join(self.source_folder, lib)
            dst = os.path.join(ext_root, "nusmuk-" + lib)
            # compiled externals, abstractions, help patches and the meta file
            copy(self, "*.pd_linux", src, dst)
            copy(self, "*.pd", src, dst)
            # wav samples referenced by the table-generation abstractions
            copy(self, "*.wav", src, dst)
            copy(self, "README.txt", src, dst, keep_path=False)
            copy(self, "LICENSE.txt", src, dst, keep_path=False)
            copy(self, "*", os.path.join(src, "examples"),
                 os.path.join(dst, "examples"))

        copy(self, "LICENSE.txt", os.path.join(self.source_folder, "utils"),
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
