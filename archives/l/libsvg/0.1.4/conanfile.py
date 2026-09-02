#!/usr/bin/env python3
"""Conan recipe for libsvg 0.1.4 — SVG parsing library from the cairographics ecosystem.

Adapted for HarmonyOS PC (aarch64) platform.
License: LGPL-2.1-or-later
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class LibsvgConan(ConanFile):
    name = "libsvg"
    version = "0.1.4"
    description = "Library for parsing SVG (Scalable Vector Graphics) files"
    license = "LGPL-2.1-or-later"
    homepage = "https://cairographics.org/"
    url = "https://cairographics.org/snapshots/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    generators = "AutotoolsDeps", "PkgConfigDeps", "VirtualBuildEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream default parser backend: libxml2 (configure.in uses
        # PKG_CHECK_MODULES(libxml-2.0 >= 2.4.7) unconditionally; expat is
        # only an optional alternative backend and is not built by default).
        self.requires("libxml2/2.15.3")
        # svg_image.c calls png_* and jpeg_* APIs directly for <image> support.
        self.requires("libpng/1.6.58")
        self.requires("libjpeg/10")
        # svg_parse_file() gzopen/gzread/gzeof/gzclose the input file, so
        # zlib is a direct dependency (and Libs: -lz in libsvg.pc confirms).
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        from conan.tools.files import get
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # 2003-era configure only knows linux-gnu; the OHOS cross target is
        # supplied explicitly (config.guess/config.sub are patched for ohos).
        if self.settings.os == "OHOS":
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
            tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        # Add -rpath flags so configure test programs can find the shared
        # libxml2/libpng/libjpeg from the Conan cache (no LD_LIBRARY_PATH).
        for dep_name in ["libxml2", "libpng", "libjpeg"]:
            dep = self.dependencies.get(dep_name)
            if dep and dep.options.get_safe("shared"):
                for libdir in dep.cpp_info.libdirs:
                    tc.extra_ldflags.append(f"-Wl,-rpath,{libdir}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # PkgConfigDeps .pc files live in the generators folder.
        gen_folder = self.generators_folder
        os.environ["PKG_CONFIG_PATH"] = gen_folder + ":" + os.environ.get("PKG_CONFIG_PATH", "")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Conan 2 copy() has no delete= argument; remove libtool *.la wrappers manually.
        import glob as _glob
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = ["svg"]
        self.cpp_info.set_property("pkg_config_name", "libsvg")
        self.cpp_info.set_property("cmake_target_name", "libsvg::libsvg")
