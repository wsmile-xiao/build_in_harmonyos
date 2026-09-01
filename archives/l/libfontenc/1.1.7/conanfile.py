#!/usr/bin/env python3
"""Conan recipe for libfontenc 1.1.7 — X11 font encoding library.

Autotools project (configure + make). Dependencies: zlib, xorgproto.
Patches: umask fix (HMDFS), config.guess/sub (HarmonyOS detection).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibfontencConan(ConanFile):
    name = "libfontenc"
    version = "1.1.7"
    description = "X11 font encoding library"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libfontenc"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libfontenc supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("xorgproto/2025.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        if str(self.settings.os) == "OHOS":
            env = tc.environment()
            shell = "/data/service/hnp/bin/bash"
            env.define_path("SHELL", shell)
            env.define_path("CONFIG_SHELL", shell)
            env.define_path("CC", "/data/service/hnp/bin/clang")
            env.define_path("CXX", "/data/service/hnp/bin/clang++")
            env.define_path("LD", "/data/service/hnp/bin/ld.lld")
            env.define_path("AR", "/data/service/hnp/bin/llvm-ar")
            env.define_path("RANLIB", "/data/service/hnp/bin/llvm-ranlib")
            env.define_path("STRIP", "/data/service/hnp/bin/llvm-strip")
            env.define_path("NM", "/data/service/hnp/bin/llvm-nm")
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
        self.cpp_info.libs = ["fontenc"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "fontenc")
        self.cpp_info.set_property("pkg_config_name", "fontenc")
