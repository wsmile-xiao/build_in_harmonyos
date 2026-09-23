#!/usr/bin/env python3
"""Conan recipe for plotutils 2.6 — GNU Autotools (configure + make + libtool).

GNU plotutils: 2-D vector graphics library (libplot) + CLI tools.
Built with --without-x (no X11 driver); PNG/PS/SVG/PNM/CGM output still works.
C++ libplotter (--enable-libplotter) disabled by default.
"""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class PlotutilsConan(ConanFile):
    name = "plotutils"
    version = "2.6"
    description = "GNU plotutils — 2-D vector graphics library and plotting utilities"
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/plotutils/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpng/1.6.58.2")
        self.requires("openssl/3.5.6.1.1", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--prefix=/")
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        tc.configure_args.append("--without-x")
        tc.configure_args.append("--enable-libplotter=no")
        tc.configure_args.append("--enable-libxmi")
        cppstd = str(self.settings.get_safe("compiler.cppstd", ""))
        if cppstd in ("17", "20", "23", "gnu17", "gnu20", "gnu23"):
            tc.cppstd = "-std=gnu++14"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        autotools = Autotools(self)
        prev_pkg_config_path = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = (
            f"{self.generators_folder}:{prev_pkg_config_path}"
        ).rstrip(":")
        prev_ld_library_path = os.environ.get("LD_LIBRARY_PATH", "")
        dep_lib_dirs = []
        for _dep in self.dependencies.values():
            if _dep.package_folder is None:
                continue
            for _d in _dep.cpp_info.libdirs:
                dep_lib_dirs.append(os.path.join(_dep.package_folder, _d))
        os.environ["LD_LIBRARY_PATH"] = (
            ":".join(dep_lib_dirs + [prev_ld_library_path]).rstrip(":")
            if dep_lib_dirs
            else prev_ld_library_path
        )
        try:
            autotools.configure()
        finally:
            if prev_pkg_config_path:
                os.environ["PKG_CONFIG_PATH"] = prev_pkg_config_path
            else:
                os.environ.pop("PKG_CONFIG_PATH", None)
            if prev_ld_library_path:
                os.environ["LD_LIBRARY_PATH"] = prev_ld_library_path
            else:
                os.environ.pop("LD_LIBRARY_PATH", None)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["plot", "xmi"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "libplot")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
