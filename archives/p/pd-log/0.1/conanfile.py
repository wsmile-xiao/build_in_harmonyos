#!/usr/bin/env python3
"""Conan recipe — pd-log 0.1 (Pd library template Makefile, Pd external library).

pd-log is IOhannes m zmölnig's small Pure Data library for logging.  It ships
five Pd externals — [logpost] [debug] [normal] [error] [fatal] — plus their
help patches and the library meta file.  Upstream ships the stock Pd
"Makefile template" (1.0.12), i.e. a plain recursive makefile with no
autotools/cmake.

OHOS notes (no source patch needed, zero patches):
- The Pd headers (m_pd.h and friends) come from the puredata package, so the
  upstream hardcoded "PD_PATH = /usr" is overridden on the make command line
  with the dependency's package folder (command-line variables win over
  makefile assignments in GNU make, so the override reaches the derived
  PD_INCLUDE / objectsdir chain).
- The template has no notion of OHOS, but on uname=Linux it already selects the
  ".pd_linux" external extension, which is exactly what Pd uses on OHOS.  No
  platform macro and therefore no platform #ifdef is required.
- The install rule strips every external with the host strip.  On OHOS the ELF
  code signature added by the OHOS clang wrapper does not survive a strip, so
  STRIP is neutralised the same way abduco / jamnntpd / tty-clock do it.
- Every external resolves logpost(3) from the running Pd process at dlopen
  time; puredata's m_pd.h declares logpost, so no link-time libpd is needed
  and no extra library has to be added.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# The stock Pd template derives everything platform-specific from
# "UNAME := $(shell uname -s)" guarded by ifeq ($(UNAME),Linux):
# EXTENSION, -fPIC, -shared, -Wl,-soname and the rpath only exist inside
# that branch.  HarmonyOS reports its own kernel name to uname -s, so on the
# CI device the branch is skipped, EXTENSION stays empty, the link loses
# -shared and every Pd symbol turns into an "undefined symbol" error
# starting with "undefined symbol: main" (CI builds #70269 / #70276).
# Command-line variables override makefile assignments, so passing
# UNAME=Linux selects the branch deterministically on every host.
# That is the correct branch for OHOS: the OHOS pd binary's string table
# contains ".pd_linux" and puredata's own OHOS package ships
# lib/pd/extra/*/*.pd_linux, so .pd_linux is the extension Pd looks for.
MAKE_UNAME = " UNAME=Linux"


class PdLogConan(ConanFile):
    name = "pd-log"
    version = "0.1"
    description = ("Small Pure Data (Pd) library for logging: the logpost, "
                   "debug, normal, error and fatal externals")
    license = "BSD-3-Clause"
    homepage = "https://download.puredata.info/log"
    url = ""  # CI fills this
    topics = ("puredata", "pd", "externals", "logging")

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        # R32: OHOS must be accepted next to Linux, never compared to "Linux".
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pd-log supports Linux/OHOS only, got {self.settings.os}")

    def requirements(self):
        # Pure Data provides the m_pd.h API headers used by all five externals
        # and is the runtime that dlopen()s them.
        self.requires("puredata/0.54.1", transitive_headers=True,
                      transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        # Upstream tarball root is log-0.1/; strip_root keeps the recipe paths
        # flat instead of one level deeper.
        get(self, **self.conan_data["sources"], strip_root=True)

    def _c_compiler(self):
        """Resolve the target C driver (R33: never rely on an undefined shell var).

        The shared CI profile hardcodes /data/service/hnp/bin/clang, a path that
        exists on the CI device but nowhere else, so the conf value is only
        trusted after an existence check and PATH discovery is the fallback.
        """
        conf_cc = self.conf.get("tools.build:compiler_executables", default={})
        cc = conf_cc.get("c", "") if isinstance(conf_cc, dict) else ""
        if not cc or not os.path.isfile(cc) or not os.access(cc, os.X_OK):
            cc = (shutil.which("aarch64-unknown-linux-ohos-clang")
                  or shutil.which("clang") or shutil.which("gcc"))
        if not cc:
            raise ConanException("no usable C compiler found for pd-log")
        return cc

    def _pd_prefix(self):
        pd_prefix = self.dependencies["puredata"].package_folder
        pd_include = os.path.join(pd_prefix, "include", "pd")
        if not os.path.isfile(os.path.join(pd_include, "m_pd.h")):
            raise ConanException(
                "puredata package has no include/pd/m_pd.h: %s" % pd_include)
        return pd_prefix

    def build(self):
        pd_prefix = self._pd_prefix()
        cc = self._c_compiler()
        # Upstream has no test entry point at all (the template's UNITTESTS is
        # empty and there is no check target), so build() only compiles.
        # STRIP=: — see the module docstring: a strip would invalidate the OHOS
        # ELF code signature, and stripping is size cosmetics only.
        self.run(
            f'make -j1 CC="{cc}" PD_PATH="{pd_prefix}" STRIP=:{MAKE_UNAME}',
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        pd_prefix = self._pd_prefix()
        cc = self._c_compiler()
        # "objectsdir" is the Pd externals install root; the template appends
        # the library name itself, so this lands the externals in
        # <package>/lib/pd-externals/log/, which is where Pd looks for them.
        self.run(
            f'make install DESTDIR="{self.package_folder}" CC="{cc}" '
            f'PD_PATH="{pd_prefix}" objectsdir=/lib/pd-externals '
            f'STRIP=:{MAKE_UNAME}',
            cwd=self.source_folder,
            env="conanbuild",
        )
        # The template already installs LICENSE.txt next to the externals; add
        # the conventional licenses/ copy as well so the recipe keeps the usual
        # Conan package layout.
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Pd externals are dlopen()-ed at runtime out of this package's own
        # lib/pd-externals/log directory, which the user hands to Pd via
        # `pd -path`. There is no archive or import library to link against,
        # so nothing is exposed to consumers.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
