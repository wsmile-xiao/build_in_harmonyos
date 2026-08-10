#!/usr/bin/env python3
"""Conan recipe for olm 3.2.16 — Matrix protocol encryption library.

Source: PyPI python-olm package (contains full C/C++ source in libolm/ subdirectory).
The official GitLab source (gitlab.matrix.org) is unreachable from CN networks;
PyPI serves as an authoritative mirror with CI mirror fallback support.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OlmConan(ConanFile):
    name = "olm"
    version = "3.2.16"
    description = "Implementation of the olm and megolm cryptographic ratchets"
    license = "Apache-2.0"
    homepage = "https://gitlab.matrix.org/matrix-org/olm/"
    # url is set by CI pipeline

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        # The PyPI package extracts to python-olm-3.2.16/ which contains
        # libolm/ (C/C++ source), olm/ (Python bindings), setup.py, etc.
        # After strip_root, we move libolm/ contents to the source root.
        get(self, **self.conan_data["sources"], strip_root=True)
        libolm_dir = os.path.join(self.source_folder, "libolm")
        if os.path.isdir(libolm_dir):
            for item in os.listdir(libolm_dir):
                src = os.path.join(libolm_dir, item)
                dst = os.path.join(self.source_folder, item)
                if os.path.exists(dst):
                    if os.path.isdir(dst):
                        shutil.rmtree(dst)
                    else:
                        os.remove(dst)
                shutil.move(src, dst)
            os.rmdir(libolm_dir)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMake 4.x removed compatibility with cmake_minimum_required < 3.5.
        # Pass as CLI arg because toolchain vars are loaded too late for
        # the cmake_minimum_required() call at top of CMakeLists.txt.
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["olm"]
