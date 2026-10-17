#!/usr/bin/env python3
"""Conan recipe — farmhash 1.1.0 (Autotools, configure + make).

Google FarmHash family of hash functions, v1.1 (upstream commit 34c13dd).
Builds libfarmhash via autotools with OHOS Hash tools; static by default (R26).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class FarmhashConan(ConanFile):
    name = "farmhash"
    version = "1.1.0"
    description = "FarmHash — Google's family of hash functions (v1.1, upstream commit 34c13dd)"
    license = "MIT"
    homepage = "https://github.com/google/farmhash"
    url = "https://github.com/google/farmhash"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # farmhash (autotools) needs no extra configure args
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["farmhash"]
