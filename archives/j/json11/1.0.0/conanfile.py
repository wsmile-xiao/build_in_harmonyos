#!/usr/bin/env python3
"""Conan recipe — json11 1.0.0 (CMake build).

json11 is a tiny header + single-translation-unit JSON library for C++11.
Official build entry is CMakeLists.txt (cmake_minimum_required 2.8).
The repo also ships a Makefile whose `test` target reproduces the upstream
test suite. CMake >= 4 removed compatibility with <3.5, so the recipe pins
CMAKE_POLICY_VERSION_MINIMUM=3.5 (verified during adaptation).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class Json11Conan(ConanFile):
    name = "json11"
    version = "1.0.0"
    description = "json11 is a tiny JSON library for C++11, providing JSON parsing and serialization"
    license = "MIT"
    homepage = "https://github.com/dropbox/json11"
    url = "https://github.com/dropbox/json11"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # CMake >= 4 removed compatibility with cmake_minimum_required < 3.5;
        # upstream json11 declares 2.8, so request the compatibility floor.
        toolchain.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Native OHOS build with clang; CMake has no OHOS platform module but the
        # library uses only the C++ standard library, so Linux mapping suffices.
        if self.settings.os in ("Linux", "OHOS"):
            toolchain.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            toolchain.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        # Upstream CMakeLists installs to lib/${CMAKE_LIBRARY_ARCHITECTURE} /
        # include/${CMAKE_LIBRARY_ARCHITECTURE}; the OHOS mapping fills the
        # architecture triplet, so pin it empty to keep plain lib/ include/.
        toolchain.cache_variables["CMAKE_LIBRARY_ARCHITECTURE"] = ""
        toolchain.cache_variables["JSON11_BUILD_TESTS"] = "OFF"
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # OHOS CMakeToolchain / GNUInstallDirs place installed artifacts under
        # lib/<gnu-triplet> and include/<gnu-triplet> (e.g. aarch64-linux-ohos)
        # even when CMAKE_LIBRARY_ARCHITECTURE is empty; flatten them back to
        # plain lib/ include/ so CMakeDeps consumers resolve libjson11.a.
        from pathlib import Path
        root = Path(self.package_folder)
        for sub in ("lib", "include"):
            base = root / sub
            if not base.is_dir():
                continue
            for tri in list(base.iterdir()):
                if not tri.is_dir():
                    continue
                for item in tri.iterdir():
                    item.rename(base / item.name)
                tri.rmdir()

    def package_info(self):
        self.cpp_info.libs = ["json11"]
        self.cpp_info.set_property("pkg_config_name", "json11")
