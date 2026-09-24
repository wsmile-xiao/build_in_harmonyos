#!/usr/bin/env python3
"""Conan recipe for the QD library (double-double and quad-double arithmetic)."""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class QdConan(ConanFile):
    name = "qd"
    version = "2.3.23-dfsg.1"
    description = (
        "QD library for double-double (dd_real, ~32 digits) and "
        "quad-double (qd_real, ~64 digits) floating-point arithmetic"
    )
    license = "BSD-3-Clause"  # LBNL modified BSD (Berkeley Lab), see COPYING
    homepage = "https://www.davidhbailey.com/dhbpapers/qd.html"
    url = ""  # CI fills this
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("qd is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # qd is self-contained: only the C++ standard library and libm are used.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: system-name libraries default to static builds.
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # The Fortran interfaces (libqdmod/libqd_f_main) are auto-enabled whenever
        # any Fortran compiler is found; neither the CI worker nor the device
        # provides one, so disable them deterministically instead of relying on
        # auto-detection.
        tc.configure_args.append("--disable-fortran")
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # The upstream test suite (tests/qd_test, tests/pslq_test, tests/c_test)
        # is part of the build contract.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Conan 2 copy() has no delete= argument; remove libtool *.la wrappers manually.
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["qd"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
