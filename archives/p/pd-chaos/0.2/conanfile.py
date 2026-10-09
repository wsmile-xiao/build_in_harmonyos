#!/usr/bin/env python3
"""Conan recipe — pd-chaos 0.2 (Pure Data externals collection).

pd-chaos is the "Chaos PD Externals" collection by Ben Bogart / Michael
McGonagle: 28 Pure Data objects that iterate classic chaotic attractors
(logistic, lorenz, rossler, henon, ikeda, tent, martin, tinkerbell, ...),
plus the shared helper library `libchaos` that computes Lyapunov exponents.

Build system: the hand-written Pd "Makefile template" 1.0.11 shipped with the
upstream tarball.  One `<class>.pd_linux` shared object is produced per class
(Pd loads them by class name through the `-path` search directory), and the
`libchaos.c` helper is linked into `libchaos.so`.

OHOS notes
----------
* `puredata/0.54.1` is packaged as an *application*, so its `package_info()`
  exports no include directory; the Pd API headers (`m_pd.h` and friends) have
  to be resolved from the dependency's package folder by hand.  This is the
  same situation as `pd-libdir/1.11` and `pd-maxlib/1.6.0` in this repo.
* The upstream Makefile picks its platform branch with `ifeq ($(UNAME),Linux)`
  where `UNAME := $(shell uname -s)`.  On an OHOS worker `uname -s` is
  `HarmonyOS`, so **no** branch matches: `EXTENSION` stays empty, `-fPIC` and
  `-shared` are never added and the link step fails with
  `undefined symbol: main`.  `UNAME=Linux` is therefore mandatory on the make
  command line (same class of problem as `system=Linux` for pd-lib-builder,
  see pd-libdir notes.md section 3.1).
* `make libdir_install` runs `strip` on every produced plugin.  The build host
  toolchain is not guaranteed to ship an `aarch64` capable `strip`, and the
  packaging step must not depend on an ambient host tool, so `STRIP=true`
  keeps the step a no-op (the plugins stay unstripped, which only affects
  artifact size).
* `ALL_LDFLAGS` contains an upstream typo, `-Wl,-rpath,"$ORIGIN",--enable-new-dtags`
  (comma instead of space).  clang splits `-Wl,` arguments on commas, so lld
  still receives three separate options and the result is the intended
  `DT_RUNPATH=$ORIGIN`; verified with `readelf -d`, no patch needed.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# 28 attractor classes; each must yield exactly one <class>.pd_linux.
EXPECTED_CLASSES = 28
# The helper shared object built from libchaos.c.
HELPER_LIB = "libchaos.so"


class PdChaosConan(ConanFile):
    name = "pd-chaos"
    version = "0.2"
    description = "Chaos PD Externals: 28 Pure Data objects iterating classic chaotic attractors"
    license = "GPL-2.0-or-later"
    homepage = "https://puredata.info"
    url = ""

    # Pd loads the artifacts with dlopen(); there is no command line entry
    # point, so this is a library and no commands.json is required (R38).
    package_type = "library"

    # Conan 2 requires a `shared` option for library package types.  Pd
    # externals are inherently shared objects (Pd dlopen()s them and resolves
    # the Pd API symbols out of its own -rdynamic image), so only the shared
    # form is meaningful and validate() rejects the static one.
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: OHOS must be accepted next to Linux, never compared to it.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pd-chaos supports Linux/OHOS only, got %s" % self.settings.os)
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "Pd externals are dlopen()ed shared objects; "
                "pd-chaos has no static form (shared=False)")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # W0/R36: the Pd API headers come from the published puredata package.
        self.requires("puredata/0.54.1")

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def _pd_include_dir(self):
        """Locate m_pd.h inside the puredata package folder.

        puredata declares `cpp_info.includedirs = []` (it is an application),
        so the include path is not exported and has to be probed for.
        """
        root = self.dependencies["puredata"].package_folder
        for candidate in (os.path.join(root, "include", "pd"),
                          os.path.join(root, "include")):
            if os.path.isfile(os.path.join(candidate, "m_pd.h")):
                return candidate
        raise ConanInvalidConfiguration(
            "Pd API header m_pd.h not found under the puredata package folder: %s" % root)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _make_opts(self):
        """Command-line overrides shared by build() and package().

        The upstream Makefile defaults to `CC = cc` and to `$(shell uname -s)`
        for platform detection, so both must be overridden on *every* make
        invocation -- `make libdir_install` re-links the plugins that make
        considers out of date and would otherwise fall back to the host gcc.
        """
        return 'CC="%s" UNAME=Linux prefix= STRIP=true' % self._compiler("c", "clang")

    def build(self):
        pd_include = self._pd_include_dir()
        # R33: the compiler comes from the Conan profile's conf, never from a
        # bare ${CC} in the shell environment.
        self.run('make -j1 %s PD_INCLUDE="%s"' % (self._make_opts(), pd_include),
                 cwd=self.source_folder, env="conanbuild")

        produced = sorted(f for f in os.listdir(self.source_folder)
                          if f.endswith(".pd_linux"))
        if len(produced) != EXPECTED_CLASSES:
            raise ConanInvalidConfiguration(
                "expected %d <class>.pd_linux plugins, produced %d"
                % (EXPECTED_CLASSES, len(produced)))
        helper = os.path.join(self.source_folder, HELPER_LIB)
        if not os.path.isfile(helper):
            raise ConanInvalidConfiguration("helper library not built: %s" % HELPER_LIB)
        self.output.info("built %d Pd externals + %s" % (len(produced), HELPER_LIB))

    def package(self):
        # prefix= (empty) makes the upstream Makefile's
        #   libdir    = $(prefix)/lib
        #   pkglibdir = $(libdir)/pd-externals
        # resolve to /lib/pd-externals, so DESTDIR lands the artifacts in
        # <package_folder>/lib/pd-externals/chaos/ -- the layout Pd expects.
        self.run("make libdir_install DESTDIR=%s %s"
                 % (self.package_folder, self._make_opts()),
                 cwd=self.source_folder, env="conanbuild")
        # chaos.h is the public header of the lyapunov() helper API.
        copy(self, "chaos.h", self.source_folder,
             os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include", self._pd_include_dir()]
        self.cpp_info.libdirs = ["lib/pd-externals/chaos"]
        # Pd resolves the plugin symbols out of its own -rdynamic executable
        # image at dlopen() time; there is nothing to link against.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []