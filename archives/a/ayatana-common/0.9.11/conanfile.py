#!/usr/bin/env python3
"""Conan recipe — ayatana-common 0.9.11 (libayatana-common, CMake).

Ayatana System Indicators' shared common library: desktop-session detection,
program lookup, URL/command helpers and a GSettings schema
(org.ayatana.common). Used by ayatana-indicator-common and friends.

Adapted to HarmonyOS PC (aarch64). See notes.md for the platform adaptations.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps


class AyatanaCommonConan(ConanFile):
    name = "ayatana-common"
    version = "0.9.11"
    description = "Ayatana System Indicators common library (libayatana-common)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/AyatanaIndicators/libayatana-common"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}"
            )

    def requirements(self):
        # glib/2.84.0.1 exposes per-module pkg-config components
        # (glib-2.0/gobject-2.0/gio-2.0/...), which the upstream CMakeLists
        # needs via pkg_check_modules(glib-2.0 gio-2.0).
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._augment_glib_pkg_config()
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream default is OFF; keep the recipe build focused on the library.
        # The upstream test suite (gtest/gmock + vala) is not run inside the
        # recipe build; functional coverage is provided by test_package.
        toolchain.variables["ENABLE_TESTS"] = "OFF"
        toolchain.variables["ENABLE_WERROR"] = "OFF"
        toolchain.generate()

    def _augment_glib_pkg_config(self):
        # utils.c includes <glib/gi18n-lib.h>, which maps gettext() to
        # g_libintl_* provided by glib's proxy-libintl (libintl.so). The
        # PkgConfigDeps-generated glib-2.0.pc does not list -lintl, so the
        # shared lib would keep undefined g_libintl_* symbols that break the
        # final consumer link. Append -lintl (mirrors the gdk-pixbuf recipe).
        for pc_name in ("glib-2.0.pc", "gio-2.0.pc", "gobject-2.0.pc"):
            pc_file = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc_file):
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            libs_line = next(
                (line for line in content.splitlines() if line.startswith("Libs:")),
                None,
            )
            if libs_line is None:
                continue
            if "-lintl" in libs_line.split():
                continue
            updated = content.replace(libs_line, libs_line + " -lintl", 1)
            with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(updated)

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def package(self):
        with self._build_environment().vars(self).apply():
            cmake = CMake(self)
            cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = ["ayatana-common"]
        # utils.h is installed under include/ayatana/common; expose include/ so
        # that `#include <ayatana/common/utils.h>` resolves (as in test_package).
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
        ]
        self.cpp_info.set_property("cmake_file_name", "ayatana-common")
        self.cpp_info.set_property(
            "cmake_target_name", "ayatana-common::ayatana-common"
        )
        self.cpp_info.set_property("pkg_config_name", "libayatana-common")
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    def _build_environment(self):
        environment = Environment()
        temporary_directory = os.path.join(self.build_folder, "tmp")
        os.makedirs(temporary_directory, exist_ok=True)
        environment.define_path("TMPDIR", temporary_directory)
        environment.define_path("TMP", temporary_directory)
        environment.define_path("TEMP", temporary_directory)
        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                environment.prepend_path("PATH", bin_dir)
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        return environment

    def _sign_installed_elfs(self):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        targets = []
        for pattern in (
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ):
            targets.extend(glob.glob(pattern, recursive=True))
        for target in targets:
            if os.path.islink(target):
                continue
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
            self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')
