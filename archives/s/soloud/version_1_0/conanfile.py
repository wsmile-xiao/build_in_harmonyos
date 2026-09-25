#!/usr/bin/env python3
"""Conan recipe — soloud version_1_0 (CMake, headless core).

SoLoud is a free, portable, extensible audio engine for games. Upstream
version_1_0 ships no build system (the demos drive SDL directly), so this
recipe applies a patch that adds a headless CMakeLists.txt: it builds the
pure-software mixing core (core + sinewave + speech + wav with bundled
stb_vorbis + filter) while excluding the optional SDL back-end and all
SDL-dependent demos, keeping the library dependency-free on OHOS.
"""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class SoloudConan(ConanFile):
    name = "soloud"
    version = "version_1_0"
    description = "Free, portable, extensible audio engine for games (headless core)"
    license = "Zlib"
    homepage = "http://soloud-audio.com"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst="licenses",
        )

    def package_info(self):
        self.cpp_info.libs = ["soloud"]
        self.cpp_info.set_property("cmake_file_name", "soloud")
        self.cpp_info.set_property("cmake_target_name", "soloud::soloud")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
        self.cpp_info.requires = []  # headless: no external deps
