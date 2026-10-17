#!/usr/bin/env python3
"""Conan recipe — little-cms2 2.19 (Little CMS colour management engine).

Little CMS 2 is Marti Maria's ICC colour-management engine: it reads and writes
ICC profiles, builds colour transforms between profiles and does the
rendering-intent work in between.  Version 2.19 is the `lcms2.19` tag.

Build system : autotools.  The release tarball ships a generated `configure`,
`Makefile.in`, `config.guess` and `config.sub`, so no autoreconf is needed at
build time.
Package form : `lib/liblcms2.a` + `include/lcms2.h` / `lcms2_plugin.h`, plus the
               three dependency-free command-line utilities `linkicc`,
               `transicc` and `psicc` (R38 -> software-level commands.json).

Optional dependencies are deliberately left out.  The `jpgicc` and `tificc`
utilities need libjpeg/libtiff; configuring with `--without-jpeg --without-tiff`
skips them (upstream's own conditional SUBDIRS handle this) so the package has
no Conan dependencies at all.  `--without-zlib` likewise keeps ICC profile
compression off rather than depending on zlib.  The core library, the whole
test suite and the remaining three tools are unaffected.

OHOS adaptation (patches/, see conandata.yml): the shipped autotools platform
scripts are older than HarmonyOS and know neither the `__OHOS__` libc probe nor
the `*:HarmonyOS:*:*` uname case, and `configure` creates its private
config.status directory with `umask 077`, which is not usable on the OHOS HMDFS.

Upstream tests: `testbed/` builds `testcms` from testcms2.c / testplugin.c /
zoo_icc.c and registers 163 checks.  They are executed for real in `build()`
(see test_package/MANIFEST.yml for the counts and how they were determined).
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LittleCms2Conan(ConanFile):
    name = "little-cms2"
    version = "2.19"
    description = ("Little CMS 2 — colour management engine (ICC profile "
                   "parsing, colour transforms) with linkicc/transicc/psicc")
    license = "MIT"
    homepage = "https://github.com/mm2/Little-CMS"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    # testbed/testcms2.c: how many `Check("...", Fn)` entries the registration
    # block contains (see test_package/MANIFEST.yml for the exact derivation).
    UPSTREAM_TEST_CASES = 163

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "little-cms2 2.19 is prepared for Linux/OHOS targets only")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--without-jpeg",
            "--without-tiff",
            "--without-zlib",
        ])
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Standard out-of-source autotools flow: Autotools.configure() invokes
        # "<source>/configure" from the *build* folder, so the generated
        # Makefiles land there and the following make/install calls (which run
        # in the build folder) find them.
        #
        # -j1 on purpose: other work shares the Harmony PC.
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Build and run upstream's own test program, then report what ran.

        `testcms` prints "Checking <title> ..." per case and "FAIL!" plus
        details when one fails; main() returns the number of failures.  Six of
        the registered cases sit behind a runtime `--exhaustive` switch (the
        slow exhaustive interpolation sweeps), so the program is invoked with
        that switch to cover the full registered set.

        The counts below are measured from the run, never declared.
        """
        # Out-of-source build: the generated Makefile and the test program
        # live in the build folder's testbed/.
        testbed = os.path.join(self.build_folder, "testbed")
        log = os.path.join(self.build_folder, "upstream-tests.log")

        # Upstream's own `check:` rule copies the ICC fixtures from the source
        # tree into the build tree for out-of-source builds
        # ("cp $(top_srcdir)/testbed/*.ic? $(top_builddir)/testbed").  Running
        # the test program directly bypasses that rule, so do the same copy
        # here -- without it testcms aborts at the first profile-reading case
        # with "File 'crayons.icc' not found".
        copy(self, "*.ic?",
             src=os.path.join(self.source_folder, "testbed"),
             dst=testbed)

        # automake builds check_PROGRAMS on demand; build it without running
        # the default suite so the cases are executed exactly once.
        self.run("make -j1 testcms", cwd=testbed)
        self.run(
            './testcms --exhaustive > "{log}" 2>&1; echo "EXIT=$?" >> "{log}"'.format(log=log),
            cwd=testbed)

        with open(log, "r", errors="replace") as handle:
            text = handle.read()

        ran = text.count("Checking ")
        failed = text.count("FAIL!")
        exit_code = None
        for line in text.splitlines():
            if line.startswith("EXIT="):
                exit_code = line[5:].strip()

        self.output.info(
            "little-cms2 upstream tests: {}/{} cases ran, {} FAIL (testcms exit {})".format(
                ran - failed, self.UPSTREAM_TEST_CASES, failed, exit_code))

        if exit_code != "0" or failed:
            raise ConanException(
                "little-cms2 upstream tests failed: testcms exit={} FAIL!={} "
                "({}/{} cases ran); full log: {}".format(
                    exit_code, failed, ran, self.UPSTREAM_TEST_CASES, log))

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["lcms2"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "lcms2")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
