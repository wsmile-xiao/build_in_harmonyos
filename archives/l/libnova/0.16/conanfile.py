#!/usr/bin/env python3
"""Conan 2 recipe for libnova 0.16 (celestial mechanics library)."""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibnovaConan(ConanFile):
    name = "libnova"
    version = "0.16"
    description = (
        "Celestial mechanics and astronomical computation library: Julian day, "
        "angle and coordinate transforms, sidereal time, precession, nutation, "
        "aberration, apparent place, rise/set/transit, solar, lunar, planetary "
        "and small-body ephemerides (VSOP87 / Pluto / elliptic-parabolic "
        "motion suites)"
    )
    license = "LGPL-2.0-or-later"
    homepage = "https://libnova.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("astronomy", "celestial-mechanics", "ephemeris", "coordinates")
    package_type = "library"
    languages = "C"
    implements = ["auto_shared_fPIC"]
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The 0.16 release tarball ships no generated autotools files (no
        # configure / Makefile.in), so the full autotools chain must run at
        # build time. tool_requires resolve against the *build* profile.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()
        tc = AutotoolsToolchain(self)
        # The 0.16 tarball ships no config.guess / config.sub at all (only
        # configure.ac); autoreconf --install installs both from the
        # tool_requires automake/1.18 package. Even that recent script
        # (config.guess 2024-07-27) cannot identify this build host (uname -s
        # = "HarmonyOS", kernel "HongMeng Kernel"; verified - it exits 1 with
        # "unable to guess system type"), so the triplets below are passed
        # explicitly. automake/1.18's config.sub accepts
        # aarch64-unknown-linux-ohos (verified). Same approach as
        # adcli/0.9.2 and a52dec/0.7.4 in this repo.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.autoreconf()

        # HMDFS can reject access to Autoconf's restrictive temporary
        # directories used by config.status. Relax both Autoconf variants.
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, "r") as fh:
            content = fh.read()

        fixed = content.replace("umask 077", "umask 022")
        fixed = fixed.replace("umask 000", "umask 022")

        if fixed == content:
            raise ConanException(
                "expected Autoconf temporary-directory umask pattern not found"
            )

        with open(configure, "w") as fh:
            fh.write(fixed)

        autotools.configure()
        autotools.make()
        # The build machine *is* the OHOS target machine, so the upstream
        # diagnostic program always runs natively (no can_run() guard -
        # conan misdetects this native build as cross: its autodetected
        # build OS is "Linux" (the fallback for the unrecognized HarmonyOS
        # uname) while the host profile says OHOS).
        #
        # Upstream registers ZERO formal `make check` test cases: no TESTS
        # or check_PROGRAMS primary exists in any Makefile.am. lntest is
        # merely a noinst_PROGRAMS diagnostic program (lntest/Makefile.am)
        # that upstream never wired into the automake `check` target, so
        # `make check` runs nothing. It is NOT a formal test suite; it is
        # a supplementary diagnostic program whose textual output we parse
        # as an extra regression gate. The harness always exits 0 even
        # when assertions fail (upstream main() returns 0 unconditionally),
        # so the [PASSED]/[FAILED] output is captured and parsed below.
        autotools.make(target="lntest", args=["-C", "lntest"])
        report = os.path.join(self.build_folder, "lntest", "lntest.out")
        with open(report, "w") as fh:
            self.run("cd lntest && ./lntest", cwd=self.build_folder,
                     stdout=fh)
        with open(report) as fh:
            output = fh.read()
        passed = output.count("[PASSED]")
        failed = output.count("[FAILED]")
        self.output.info(
            f"lntest diagnostic: {passed} passed, {failed} failed "
            f"(upstream formal make check test count: 0)"
        )
        # Exact-baseline verification of the supplementary diagnostic
        # program: the frozen v0.16 codebase produces exactly 316 PASSED
        # and 24 FAILED out of 340 internal checks on every platform
        # audited (a second build with the OHOS SDK toolchain on the
        # same aarch64 host and the cross/OHOS package build produce
        # identical output). All 24 failures are recorded as failures;
        # independent evidence that the expectation itself is wrong
        # exists for only 5 (3 nutation, disproven by upstream commit
        # 7b60adc; 2 Pollux, contradicted by an independent
        # epoch-correct reduction - the library value matches the
        # 1987-04-10 mean obliquity reduction to 8 decimals); the
        # remaining 19 have no authoritative resolution - only
        # host-vs-OHOS parity. The gate requires EXACT equality: any
        # drift in either direction (new failure OR unexpected pass)
        # fails the build, so results can never silently change on any
        # libc/architecture.
        if (passed, failed) != (316, 24):
            raise ConanException(
                f"lntest baseline drift: passed={passed} failed={failed} "
                f"(expected exactly 316 passed / 24 failed / 340 total)"
            )

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        libdir = os.path.join(self.package_folder, "lib")
        rm(self, "*.la", libdir)
        # libtool installs only the versioned soname libnova-0.16.so.0; the
        # unversioned dev symlink libnova.so is missing (upstream lacks the
        # usual libnova_la_LDFLAGS -version-info handling), so create it for
        # consumers linking with -lnova.
        if self.options.shared:
            soname = "libnova-0.16.so.0"
            link = os.path.join(libdir, "libnova.so")
            if os.path.exists(os.path.join(libdir, soname)) \
                    and not os.path.exists(link):
                os.symlink(soname, link)

    def package_info(self):
        self.cpp_info.libs = ["nova"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("pkg_config_name", "libnova")
