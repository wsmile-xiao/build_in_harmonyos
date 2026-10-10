#!/usr/bin/env python3
"""Conan recipe for xlinks 2.30 using the Autotools text-terminal build."""

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XlinksConan(ConanFile):
    name = "xlinks"
    version = "2.30"
    description = "Text-terminal web browser"
    license = "GPL-2.0-or-later"
    homepage = "https://links.twibright.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/x/xlinks/2.30"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    generators = ["PkgConfigDeps"]

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.8.1")
        self.requires("zlib/1.3.2.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Feed Conan dependency include and library paths to configure checks
        # that do not use pkg-config.
        AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--disable-graphics",
                "--without-x",
                "--without-brotli",
                "--with-ssl",
                "--without-libevent",
                "--without-gpm",
                "--without-zstd",
                "--without-bzip2",
                "--without-lzma",
                "--without-lzip",
                "--without-openmp",
            ]
        )
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        runpath = Environment()
        for dependency in self.dependencies.values():
            for libdir in dependency.cpp_info.libdirs:
                runpath.prepend_path("LD_LIBRARY_PATH", libdir)

        # AutotoolsDeps links configure probes against Conan shared libraries.
        # Keep those probe executables runnable on-device so configure records
        # native type sizes instead of misclassifying the build as cross.
        with runpath.vars(self, scope="build").apply():
            autotools.configure()
            autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
