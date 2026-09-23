#!/usr/bin/env python3
"""Conan recipe for rdfind 1.8.0 — HarmonyOS (OpenHarmony PC) aarch64 adaptation.

rdfind is a command line tool that finds duplicate files and can replace them
with hardlinks or symlinks. It is an Autotools project whose only mandatory
dependency is nettle (configure aborts without `nettle/sha1.h` and a linkable
libnettle). xxhash is optional upstream and is explicitly switched off here so
the build depends only on packages that are published in the OHOS registry.

OHOS notes:
  - AutotoolsToolchain does not inject dependency include/lib directories, and
    rdfind probes nettle with AC_CHECK_HEADER/AC_CHECK_LIB rather than
    pkg-config, so nettle's directories are appended to CFLAGS/CXXFLAGS/LDFLAGS
    explicitly (the same remedy configure itself suggests in its error text).
  - The release tarball ships the generated `configure`/`Makefile.in`, so no
    autoreconf bootstrap is needed.
  - The upstream test suite (15 shell test cases declared in Makefile.am `TESTS=`)
    is executed with `make check` on native builds and **gates the build**: the nine
    non-XFAIL cases must pass (any FAIL/XPASS/ERROR fails the build), while the six
    cases listed in `XFAIL_TESTS` below are tolerated as expected failures because
    they need capabilities the OHOS worker does not provide. Skipped only when
    cross-compiling, where the aarch64 test programs cannot run on the host.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RdfindConan(ConanFile):
    name = "rdfind"
    version = "1.8.0"
    description = "Finds duplicate files and can replace them with hardlinks or symlinks"
    license = "GPL-2.0-or-later"
    homepage = "https://rdfind.pauldreik.se/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} is adapted for Linux/OHOS only (got os={self.settings.os})"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Mandatory: sha1/sha256 checksumming (configure fails without nettle).
        self.requires("nettle/3.10.2.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # AutotoolsToolchain already passes the correct cross trio for this
        # profile (--host=aarch64-linux-ohos --build=<build machine>), so no
        # extra --host/--build is added here: a second pair would override the
        # toolchain's values and make configure believe it is a native build.
        # xxhash is optional upstream; keep it off so only published packages
        # are required.
        tc.configure_args.append("--without-xxhash")

        dep = self.dependencies["nettle"]
        aggregated = dep.cpp_info.aggregated_components()
        for includedir in aggregated.includedirs:
            tc.extra_cflags.append(f"-I{includedir}")
            tc.extra_cxxflags.append(f"-I{includedir}")
        for libdir in aggregated.libdirs:
            tc.extra_ldflags.append(f"-L{libdir}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

        # Upstream test suite (Makefile.am TESTS=, 15 cases). Mandatory on native
        # builds (R51): a real failure fails the build, so the CI verdict reflects the
        # upstream suite instead of hiding it behind a warning. Skipped only when
        # cross-building, where the aarch64 test programs cannot run here.
        #
        # Six cases are declared as *expected* failures (automake XFAIL_TESTS) because
        # they exercise capabilities the OHOS CI worker does not provide — the concrete
        # reasons were taken from the worker's own test-suite.log (CI build #50919) and
        # are documented in manifest.yaml / notes.md:
        #   hardlink_fails.sh, verify_size_savings.sh  -> HMDFS rejects hard links
        #   largefilesupport.sh                        -> dd cannot create 4 GiB sparse files
        #   sha1collisions.sh                          -> worker base64 lacks GNU "decode"
        #   symlinking_action.sh, verify_dryrun_option.sh -> worker stat lacks --dereference
        XFAIL_CASES = ("testcases/hardlink_fails.sh testcases/largefilesupport.sh "
                       "testcases/sha1collisions.sh testcases/symlinking_action.sh "
                       "testcases/verify_dryrun_option.sh testcases/verify_size_savings.sh")

        if not cross_building(self):
            try:
                autotools.make(target="check", args=["-j1", f'XFAIL_TESTS="{XFAIL_CASES}"'])
            except ConanException:
                # Surface the per-case reasons (automake writes them to test-suite.log)
                # in the build output before propagating the failure, so the reasons are
                # visible in the CI log instead of only "FAIL: <case>".
                for name in ("test-suite.log", "testcases/hardlink_fails.log",
                             "testcases/largefilesupport.log", "testcases/sha1collisions.log",
                             "testcases/symlinking_action.log", "testcases/verify_dryrun_option.log",
                             "testcases/verify_size_savings.log"):
                    path = os.path.join(self.build_folder, name)
                    if os.path.exists(path):
                        self.output.info(f"---- {name} ----")
                        self.output.info(open(path, encoding="utf-8", errors="replace").read()[:8000])
                raise
            # Print the automake summary even on success, so the declaration is
            # machine-checkable from the CI log ("# XFAIL: 6" etc.) instead of being
            # only inferable from the fact that the build passed.
            summary = os.path.join(self.build_folder, "test-suite.log")
            if os.path.exists(summary):
                self.output.info("---- make check summary ----")
                for line in open(summary, encoding="utf-8", errors="replace").read().splitlines():
                    if line.startswith(("# TOTAL", "# PASS", "# SKIP", "# XFAIL",
                                        "# FAIL", "# XPASS", "# ERROR")):
                        self.output.info(line)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
