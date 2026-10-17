#!/usr/bin/env python3
"""Conan recipe — nativefiledialog-extended 1.3.0.

Backend: GTK3 (NFD_PORTAL=OFF, upstream default). OHOS PC has no
xdg-desktop-portal daemon ecosystem, so the portal backend is rejected
(see learninglog/20260908nativefiledialog-extended-1.3.0/后端选型报告.md).

Source url/sha256 hardcoded here (no conandata.yml) to avoid the CI
build_and_test.sh "Pre-download" stage crashing on an unset BUILD_DIR
variable (agg/iso-codes/xmodem precedent).

The upstream Linux branch probes GTK3 via pkg_check_modules(GTK3 REQUIRED
gtk+-3.0); generate() therefore emits PkgConfigDeps .pc files (the gtk
package declares pkg_config_name "gtk+-3.0") and injects PKG_CONFIG_PATH
into the conanbuild env used by the CMake helper.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get
from conan.tools.gnu import PkgConfigDeps


class NativefiledialogExtendedConan(ConanFile):
    name = "nativefiledialog-extended"
    version = "1.3.0"
    description = "A small C library that portably invokes native file dialogs"
    license = "Zlib"
    homepage = "https://github.com/btzy/nativefiledialog-extended"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"  # recipe repo

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        # R32: platform check must use `in ("Linux", "OHOS")`, not `== "Linux"`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def requirements(self):
        # GTK3 backend. The conan package name is "gtk" (the archives dir is
        # "gtk+" but the registry recipe is gtk/3.24.38); it declares
        # pkg_config_name "gtk+-3.0" so PkgConfigDeps emits gtk+-3.0.pc.
        self.requires("gtk/3.24.38")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(
            self,
            url="https://github.com/btzy/nativefiledialog-extended/archive/refs/tags/v1.3.0.tar.gz",
            sha256="2fea19102cf4d5283a80fb87a784792166988e85bb92baa962d34f72b22dcc1a",
            strip_root=True,
        )

    def generate(self):
        # Emit dependency .pc files (gtk+-3.0.pc etc.) for upstream's
        # pkg_check_modules(GTK3 REQUIRED gtk+-3.0) probe.
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        # E092: CMake doesn't recognize OHOS as a target platform
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        # Pin C++17 (upstream auto-picks 20/23 from CMake version; nfd needs
        # only 17 — avoids depending on OHOS clang/libc++ C++23 surface).
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "17"
        # Upstream defaults NFD_BUILD_TESTS to ON when built as a root project:
        # 21 GUI dialog-interaction test programs (each blocks waiting for user
        # input on a live display — not runnable headless) + NFD_BUILD_SDL2_TESTS
        # adds 1 SDL2 test. Keep both off.
        tc.cache_variables["NFD_BUILD_TESTS"] = "OFF"
        tc.cache_variables["NFD_BUILD_SDL2_TESTS"] = "OFF"
        tc.generate()
        # pkg_check_modules resolves .pc files via PKG_CONFIG_PATH; point it
        # at the PkgConfigDeps generators folder (R49: build-folder-private,
        # never a shared prefix).
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self).save_script("conan_nfd_pkg_config")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "nfd")
        self.cpp_info.set_property("cmake_target_name", "nfd::nfd")
        self.cpp_info.set_property("pkg_config_name", "nfd")
        self.cpp_info.libs = ["nfd"]
        self.cpp_info.includedirs = ["include"]
        # Static libnfd.a drags GTK3 symbols at link time; declare the
        # dependency so consumers link the full chain. gtk has no explicit
        # components, so reference its implicit component (pkgname::pkgname).
        self.cpp_info.requires = ["gtk::gtk"]
