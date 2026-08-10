#!/usr/bin/env python3
"""Conan recipe for potrace 1.16 — Autotools (configure + make).

potrace is a tool for tracing a bitmap, producing a set of smooth
polygons (paths) that approximate the bitmap image.
It includes a command-line tool (potrace, mkbitmap) and a library (libpotrace).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PotraceConan(ConanFile):
    name = "potrace"
    version = "1.16"
    description = "A tool for tracing a bitmap, producing a smooth polygon path"
    license = "GPL-2.0-or-later"
    homepage = "https://potrace.sourceforge.net"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        # Enable library and headers installation
        tc.configure_args.append("--with-libpotrace")
        # R26: static linking for system-name libraries
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
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
        self.cpp_info.set_property("cmake_file_name", "potrace")
        self.cpp_info.set_property("cmake_target_name", "potrace::potrace")
        self.cpp_info.libs = ["potrace"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        # zlib is a system library on HarmonyOS/Linux
        self.cpp_info.system_libs = ["z", "m"]
