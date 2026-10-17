#!/usr/bin/env python3
"""Conan recipe — slop 7.7 (CMake)."""

import os
import platform
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class SlopConan(ConanFile):
    name = "slop"
    version = "7.7"
    description = "Interactive X11 screen region selection utility and library"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/naelstrof/slop"
    url = "https://github.com/naelstrof/slop"
    # Upstream installs both libslopy and the slop CLI. Model the package as a
    # library so Conan propagates the public headers/link metadata to consumers;
    # commands.json separately declares the executable entry point.
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "libx11/6.4.0",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libxext/6.4.0.1",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires("glm/1.0.3", transitive_headers=True)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"slop supports Linux and OHOS, not {self.settings.os}"
            )

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["SLOP_OPENGL"] = False
        toolchain.variables["SLOP_UNICODE"] = False
        toolchain.variables["CMAKE_INSTALL_PREFIX"] = "/"
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream v7.7 has no registered tests. Running ctest preserves the
        # upstream test entry point and records the empty-suite result.
        self.run(
            f'ctest --test-dir "{self.build_folder}" --output-on-failure'
        )

    def package(self):
        CMake(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._sign_ohos_binary(
            os.path.join(self.package_folder, "bin", "slop")
        )

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["slopy"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = [
            "libx11::libx11",
            "libxext::libxext",
            "glm::glm",
        ]
        self.cpp_info.set_property("cmake_file_name", "slop")
        self.cpp_info.set_property("cmake_target_name", "slop::slop")
        self.cpp_info.set_property("pkg_config_name", "slop")

    @staticmethod
    def _sign_ohos_binary(binary):
        if not os.path.isfile(binary) or platform.system() != "HarmonyOS":
            return
        signer = shutil.which("binary-sign-tool")
        if not signer:
            return
        signed = binary + ".signed"
        result = subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                binary,
                "-outFile",
                signed,
                "-selfSign",
                "1",
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0 and os.path.isfile(signed):
            os.replace(signed, binary)
            os.chmod(binary, 0o755)
