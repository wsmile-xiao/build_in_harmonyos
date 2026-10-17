#!/usr/bin/env python3
"""Conan recipe — parasail 2.6.2 (pairwise sequence alignment library).

parasail is a SIMD C library for global, semi-global and local pairwise
sequence alignment (NW/SG/SW) supporting SSE2/SSE41/AVX2/AltiVec/NEON
instruction sets with runtime CPU dispatch.

Build system: autotools (configure.ac + Makefile.am + m4/).
The GitHub tag archive ships NO pre-generated configure script — build()
runs `autoreconf -fi` with automake/libtool provided by tool_requires
(CI worker has no automake/libtoolize in PATH).

Dependencies:
  - none (zero runtime dependencies; optional zlib disabled via --without-zlib)

NEON on aarch64: auto-detected by configure via <arm_neon.h> compile probe;
no hand-picked SIMD flags (configure picks NEON_CFLAGS itself).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ParasailConan(ConanFile):
    name = "parasail"
    version = "2.6.2"
    description = (
        "Pairwise sequence alignment library for global, semi-global and "
        "local alignments with SIMD (SSE2/SSE41/AVX2/AltiVec/NEON) support"
    )
    license = "BSD-3-Clause"
    homepage = "https://github.com/jeffdaily/parasail"
    url = "https://github.com/jeffdaily/parasail"
    topics = ("bioinformatics", "alignment", "simd", "neon")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The GitHub tag archive contains only configure.ac + Makefile.am +
        # m4/ (no generated configure). build() must run `autoreconf -fi`:
        # aclocal/automake come from automake/1.18, libtoolize + libtool.m4
        # (LT_INIT) come from libtool/2.5.4. The CI worker PATH has no
        # automake/libtool, and /data/service/hnp/bin has only the autoconf
        # family — both tools must come from tool_requires (yara/abiword
        # precedent). Resolved with the *build* profile: conan create must
        # pass both -pr:h and -pr:b.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # VirtualBuildEnv: put tool_requires (automake/libtool) bin dirs into
        # the conanbuild PATH so `autoreconf -fi` finds aclocal/automake/
        # libtoolize; it also carries the ACLOCAL_PATH exported by libtool
        # (LT_INIT needs libtool.m4 at aclocal time).
        VirtualBuildEnv(self).generate()
        # config.guess cannot identify HarmonyOS (uname -s = HarmonyOS,
        # "unable to guess system type" → configure: error: cannot guess
        # build type), and Conan does not pass --host/--build on its own for
        # this target. Pin both triplets explicitly (config.sub 2024-07-27
        # accepts aarch64-linux-ohos). Identical --build/--host keeps
        # cross_compiling=no so upstream keeps TESTS enabled for
        # `make check` (tests/test_isa, tests/test_basic,
        # tests/test_verify.test).
        self.conf.define("tools.gnu:host_triplet", "aarch64-linux-ohos")
        self.conf.define("tools.gnu:build_triplet", "aarch64-linux-ohos")
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Optional zlib (gzipped input in the aligner app) is disabled by
        # default: keeps the package dependency-free. Core alignment library
        # and tests do not use zlib on this path (HAVE_ZLIB=0).
        tc.configure_args.append("--without-zlib")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Bootstrap autotools. AC_INIT extracts the version via
        # m4_esyscmd([./version.sh]) (uses egrep/awk/tr — available in PATH
        # on device and CI via /data/service/hnp/bin + /system/bin).
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.run("autoreconf -fi", cwd=self.source_folder,
                     env="conanbuild")
        # E011: generated configure/Makefile.in embed `umask 077` for temp
        # dirs, which lands as unusable dir modes on HMDFS — normalize to
        # umask 022 (same fix as yara 4.5.5).
        for fname in ("configure", "Makefile.in"):
            fpath = os.path.join(self.source_folder, fname)
            if os.path.isfile(fpath):
                replace_in_file(self, fpath, "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j4"])
        # The upstream regression suite is part of the build contract
        # (a52dec precedent). TESTS = tests/test_isa tests/test_basic
        # tests/test_verify.test (guard: upstream disables TESTS when
        # cross_compiling; --host == --build on this profile keeps it
        # enabled).
        autotools.make(target="check", args=["-j4"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["parasail"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_target_name", "parasail::parasail")
        self.cpp_info.set_property("pkg_config_name", "parasail-1")
