#!/usr/bin/env python3
"""Conan recipe for the Lensfun command-line tools (lenstool + database helpers).

The tools are built from the upstream Lensfun v0.3.4 source with
BUILD_LENSTOOL=ON and BUILD_STATIC=ON: lenstool statically links the in-tree
liblensfun, so the package ships self-contained tool binaries plus the lens
database instead of a second copy of the library.
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LensfunToolsConan(ConanFile):
    name = "lensfun-tools"
    version = "0.3.4"
    description = "Lensfun project command-line tools: lenstool and lens database helper scripts"
    license = "LGPL-3.0-or-later"
    homepage = "https://lensfun.github.io/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # glib2 is the core runtime dependency of liblensfun (linked into
        # lenstool); libpng/zlib are required by lenstool's image I/O.
        # libpng pins zlib/1.3.1 to match glib2/2.88.0.1's transitive zlib
        # (libpng >= 1.6.58 requires zlib/1.3.2 and conflicts with glib2).
        self.requires("glib2/2.88.0.1")
        self.requires("libpng/1.6.39")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream declares cmake_minimum_required(VERSION 2.8.12); CMake >= 4
        # needs the compatibility policy switch (see archives/l/lensfun notes).
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_LENSTOOL"] = True      # lenstool + helper scripts
        tc.variables["BUILD_STATIC"] = True        # lenstool links liblensfun statically
        tc.variables["BUILD_TESTS"] = False        # upstream glib tests target the library, not the tools
        tc.variables["BUILD_DOC"] = False
        tc.variables["INSTALL_PYTHON_MODULE"] = False  # setup.py needs setuptools; recipe ships the module itself
        # Upstream consumes glib through its own FindGLIB2 variables
        # (GLIB2_INCLUDE_DIRS / GLIB2_LIBRARIES). CMakeDeps publishes
        # glib2Config.cmake, and on the case-insensitive HMDFS the package
        # name also satisfies find_package(GLIB2) config mode, so the module
        # never runs and those variables stay empty. Provide them explicitly
        # (static libs listed in link order: glib, then its pcre2/ffi/intl
        # dependencies) — this is deterministic on any filesystem.
        glib_pkg = self.dependencies["glib2"].package_folder
        pcre2_pkg = self.dependencies["pcre2"].package_folder
        tc.cache_variables["GLIB2_INCLUDE_DIRS"] = ";".join([
            os.path.join(glib_pkg, "include", "glib-2.0"),
            os.path.join(glib_pkg, "lib", "glib-2.0", "include"),
        ])
        tc.cache_variables["GLIB2_GLIB2CONFIG_INCLUDE_PATH"] = os.path.join(
            glib_pkg, "lib", "glib-2.0", "include")
        tc.cache_variables["GLIB2_LIBRARIES"] = ";".join([
            os.path.join(glib_pkg, "lib", "libglib-2.0.a"),
            os.path.join(pcre2_pkg, "lib", "libpcre2-8.a"),
            os.path.join(glib_pkg, "lib", "libffi.a"),
            os.path.join(glib_pkg, "lib", "libintl.a"),
        ])
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Ship only the tools: the static lensfun is linked into lenstool, so
        # the library product and headers are dropped from the package.
        shutil.rmtree(os.path.join(self.package_folder, "include"), ignore_errors=True)
        # The python helper module is relocated to a package-relative path and
        # made importable through PYTHONPATH (see package_info); upstream's
        # setup.py route is disabled because OHOS has no setuptools.
        module_dst = os.path.join(self.package_folder, "share", "lensfun", "python", "lensfun")
        init_in = os.path.join(self.source_folder, "apps", "lensfun", "__init__.py.in")
        if os.path.isfile(init_in):
            os.makedirs(module_dst, exist_ok=True)
            with open(init_in, "r", encoding="utf-8") as fh:
                text = fh.read()
            text = text.replace("${CMAKE_INSTALL_FULL_DATAROOTDIR}",
                                os.path.join(self.package_folder, "share"))
            text = text.replace("${CMAKE_INSTALL_LOCALSTATEDIR}",
                                os.path.join(self.package_folder, "var"))
            text = text.replace("${LENSFUN_DB_VERSION}", "1")
            with open(os.path.join(module_dst, "__init__.py"), "w", encoding="utf-8") as fh:
                fh.write(text)
        shutil.rmtree(os.path.join(self.package_folder, "lib"), ignore_errors=True)
        for exe in glob.glob(os.path.join(self.package_folder, "bin", "*")):
            os.chmod(exe, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.append_path(
            "PYTHONPATH", os.path.join(self.package_folder, "share", "lensfun", "python")
        )
