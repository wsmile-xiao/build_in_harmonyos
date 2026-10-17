#!/usr/bin/env python3
"""Conan recipe for libexmdbpp 1.11 (grommunio exmdb wire protocol library).

Build system: CMake (>=3.14). Upstream hard-codes ``add_library(exmdbpp SHARED ...)``
and only builds the Python bindings when pybind11 is available, therefore:

- ``shared`` defaults to True; ``shared=False`` is rejected in ``validate()`` because
  upstream's CMakeLists.txt ships no static code path.
- ``BUILD_PYEXMDB`` is pinned OFF: the bindings are an optional extra that pulls in
  Python development headers and pybind11, which are out of scope for this package.

No third-party dependencies are required beyond the C++17 standard library.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, export_conandata_patches, get,
                               replace_in_file)


class LibexmdbppConan(ConanFile):
    name = "libexmdbpp"
    version = "1.11"
    description = "A C++ implementation of the exmdb wire protocol for use with grommunio"
    license = "AGPL-3.0-or-later"
    homepage = "https://github.com/grommunio/libexmdbpp"
    url = "https://github.com/grommunio/libexmdbpp"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        # R32: keep the OHOS platform branch explicit.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libexmdbpp supports Linux/OpenHarmony only, got {self.settings.os}")
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "libexmdbpp 1.11 upstream CMakeLists.txt hard-codes "
                "add_library(exmdbpp SHARED ...); only shared builds are supported")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        # Upstream uses add_library(exmdbpp SHARED ...) directly and ignores
        # BUILD_SHARED_LIBS; keep the flag in sync for consistency anyway.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Optional Python bindings: pin OFF (no pybind11 / Python-dev dependency).
        tc.variables["BUILD_PYEXMDB"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # OHOS/HMDFS: streaming clang diagnostics directly into Conan's captured pipe
        # can abort compilation without leaving any message behind (make only prints
        # "Error 1"). Bind the build output to a log file inside the build folder.
        build_log = os.path.join(self.build_folder, "build.log")
        self.output.info(f"Building libexmdbpp, compiler diagnostics -> {build_log}")
        try:
            with open(build_log, "w") as log:
                cmake.build(stdout=log, stderr=log)
        except ConanException:
            # Surface the captured diagnostics: make only reports "Error 1".
            if os.path.isfile(build_log):
                with open(build_log) as log:
                    self.output.error(log.read()[-4000:])
            raise

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._fix_exported_soname()

    def _fix_exported_soname(self):
        """Tell downstream CMake users the real SONAME of the packaged library.

        The DT_SONAME comes from patches/0001-CMakeLists.txt.patch, but CMake
        itself never sees a versioned library on HarmonyOS (no Platform/HarmonyOS
        module -> empty CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG), so its exported
        target still claims IMPORTED_NO_SONAME. Downstream would then be forced
        to link the absolute path. The ELF does carry -Wl,-soname,libexmdbpp.so,
        so replace the placeholder with that value.
        """
        targets = os.path.join(self.package_folder, "share", "exmdbpp", "cmake",
                               "exmdbppTargets-release.cmake")
        if not os.path.isfile(targets):
            return
        replace_in_file(self, targets,
                        'IMPORTED_NO_SONAME_RELEASE "TRUE"',
                        'IMPORTED_SONAME_RELEASE "libexmdbpp.so"',
                        strict=False)

    def package_info(self):
        self.cpp_info.libs = ["exmdbpp"]
        self.cpp_info.set_property("cmake_file_name", "libexmdbpp")
        self.cpp_info.set_property("cmake_target_name", "libexmdbpp::libexmdbpp")
        self.cpp_info.set_property("pkg_config_name", "libexmdbpp")
