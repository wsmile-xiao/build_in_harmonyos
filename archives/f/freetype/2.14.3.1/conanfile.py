#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Freetype, freetype, 2.14.3, Free, high-quality font rendering engine supporting TrueType, OpenType, CFF and others, FreeType-License OR GPL-2.0, https://freetype.org/
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class FreetypeConan(ConanFile):
    name = "freetype"
    version = "2.14.3.1"
    description = "Free, high-quality font rendering engine supporting TrueType, OpenType, CFF and others"
    license = "FreeType-License OR GPL-2.0"
    homepage = "https://freetype.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

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
        # OHOS: freetype 的 builds/unix/detect.mk 自动检测用默认 cc 而非
        # clang（CI #29062: "C compiler cannot create executables" Error 77）。
        # 参照 libxext 先例注入编译器/工具环境变量。
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
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        tc.configure_args.append("--with-zlib=no")
        tc.configure_args.append("--with-bzip2=no")
        tc.configure_args.append("--with-png=no")
        tc.configure_args.append("--with-harfbuzz=no")
        tc.configure_args.append("--with-brotli=no")
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
        self.cpp_info.libs = ["freetype"]
        # freetype 头装在 include/freetype2/（ft2build.h + freetype/*.h），非标准 include/ 根。
        self.cpp_info.includedirs = ["include/freetype2", "include"]
        # freetype2.pc 的 Version 是 libtool 号（version_info=26:6:20 → 26.6.20），非 release 2.14.3。
        self.cpp_info.set_property("system_package_version", "26.6.20")
        self.cpp_info.set_property("cmake_file_name", "freetype")
