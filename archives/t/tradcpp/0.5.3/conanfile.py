#!/usr/bin/env python3
"""Conan recipe — tradcpp 0.5.3 (traditional / K&R C preprocessor).

tradcpp is David Holland's preprocessor that follows the *traditional*
(Reiser) preprocessing algorithm instead of the ISO one, so it can preprocess
the ancient K&R C that modern cpp no longer handles — the reason the NetBSD
build system keeps it around.

Build system : upstream ships a *NetBSD* makefile — a nine-line file ending in
               ``.include <bsd.prog.mk>`` that requires bmake and cannot be
               read by GNU make at all.  There is no configure, no CMake and no
               autotools.
Package form : a single CLI executable (``bin/tradcpp``) plus its man page,
               so the package is an application (R38 -> commands.json).

OHOS adaptation (patches/0001-add-GNUmakefile.patch):

  ``GNUmakefile`` is added next to the untouched upstream ``Makefile``.  GNU
  make prefers ``GNUmakefile`` over ``Makefile`` when both are present, so the
  worker builds with plain GNU make while NetBSD users keep their bsd.prog.mk
  build.  The nine source files are listed exactly as upstream's ``SRCS``
  does; compiler and flags come from the Conan toolchain environment
  (``$(CC)``/``$(CPPFLAGS)``/``$(CFLAGS)``/``$(LDFLAGS)``), never from
  hard-coded names (R33).

Upstream tests: 40 cases, ``tests/Makefile`` — see test_package/MANIFEST.yml.
They are executed for real inside ``build()`` and their results are reported
as measured, not declared.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class TradcppConan(ConanFile):
    name = "tradcpp"
    version = "0.5.3"
    description = ("tradcpp — a traditional (K&R-style) C preprocessor "
                   "implementing the Reiser algorithm")
    license = "BSD-2-Clause"
    homepage = "https://www.NetBSD.org/~dholland/tradcpp/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    # tests/Makefile: TESTS= t01 .. t40
    UPSTREAM_TESTS = ["t{:02d}".format(i) for i in range(1, 41)]

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "tradcpp 0.5.3 is prepared for Linux/OHOS targets only")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # NOTE: Autotools.make() runs make in the *build* folder, not in the
        # source folder where GNUmakefile lives.  Run it in the source folder;
        # the AutotoolsToolchain environment (CC from
        # tools.build:compiler_executables, plus CPPFLAGS/CFLAGS/LDFLAGS) is
        # applied to self.run() either way.
        #
        # -j1 on purpose: this session shares the Harmony PC with a large
        # unrelated build and must not add parallel load.
        self.run("make -j1", cwd=self.source_folder)
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Reproduce tests/Makefile's harness exactly, on the target.

        For every case upstream runs

            $(TRADCPP) $(T).c > $(T).run 2>&1 || echo FAILED >> $(T).run

        with the working directory set to tests/, then compares $(T).run with
        the recorded $(T).good.  Both details matter: t38 exercises __FILE__,
        so a bare ``t38.c`` argument resolved from inside tests/ is what the
        recorded output expects.

        Results are measured here (not declared): a mismatch fails the build.
        """
        tests_dir = os.path.join(self.source_folder, "tests")
        binary = os.path.join(self.source_folder, "tradcpp")
        rundir = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(rundir, exist_ok=True)

        passed, failed = [], []
        for name in self.UPSTREAM_TESTS:
            run_file = os.path.join(rundir, name + ".run")
            self.run(
                '"{binary}" {name}.c > "{run}" 2>&1 || echo FAILED >> "{run}"'.format(
                    binary=binary, name=name, run=run_file),
                cwd=tests_dir,
            )
            with open(os.path.join(tests_dir, name + ".good"), "r") as handle:
                expected = handle.read()
            with open(run_file, "r") as handle:
                actual = handle.read()
            if expected == actual:
                passed.append(name)
            else:
                failed.append(name)

        self.output.info("tradcpp upstream tests: {}/{} passed".format(
            len(passed), len(self.UPSTREAM_TESTS)))
        if failed:
            raise ConanException(
                "tradcpp upstream tests failed: {} (of {}). First mismatching "
                "case: {} — see {}/<case>.run against tests/<case>.good".format(
                    ", ".join(failed), len(self.UPSTREAM_TESTS), failed[0], rundir))

    def package(self):
        copy(self, "tradcpp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "tradcpp.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
