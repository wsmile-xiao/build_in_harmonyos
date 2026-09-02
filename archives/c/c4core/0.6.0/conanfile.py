#!/usr/bin/env python3
"""Conan recipe for c4core 0.6.0 — CMake static library."""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


class C4CoreConan(ConanFile):
    name = "c4core"
    version = "0.6.0"
    description = "Multiplatform low-level C++ utilities"
    topics = ("utilities", "cpp")
    url = "https://github.com/biojppm/c4core"
    homepage = "https://github.com/biojppm/c4core"
    license = "MIT"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    _CMAKE_MODULES = (
        "ConfigurationTypes.cmake",
        "CreateSourceGroup.cmake",
        "GetFlags.cmake",
        "GetNames.cmake",
        "PatchUtils.cmake",
        "PrintVar.cmake",
        "PVS-Studio.cmake",
        "c4CatSources.cmake",
        "c4Doxygen.cmake",
        "c4GetTargetPropertyRecursive.cmake",
        "c4StaticAnalysis.cmake",
        "c4Project.cmake",
    )

    def export_sources(self):
        patches_dir = os.path.join(self.recipe_folder, "patches")
        exported_patches_dir = os.path.join(self.export_sources_folder, "patches")
        copy(self, "*.patch", patches_dir, exported_patches_dir)
        for module in self._CMAKE_MODULES:
            copy(self, module, patches_dir, exported_patches_dir)

        # The c4core release archive leaves this git submodule empty, but the
        # upstream CMakeLists.txt lists and compiles the header.
        copy(
            self,
            "debugbreak.h",
            os.path.join(patches_dir, "submodules", "debugbreak"),
            os.path.join(self.export_sources_folder, "submodules", "debugbreak"),
        )

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("c4core is supported only on Linux/OHOS")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["C4CORE_INSTALL"] = True
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.generate()

    def build(self):
        # Copy all cmake modules to cmake directory (submodule workaround)
        src_cmake_dir = os.path.join(self.export_sources_folder, "patches")
        dst_cmake_dir = os.path.join(self.source_folder, "cmake")

        os.makedirs(dst_cmake_dir, exist_ok=True)
        for module in self._CMAKE_MODULES:
            if not os.path.isfile(os.path.join(src_cmake_dir, module)):
                raise ConanException(f"Missing bundled CMake module: {module}")
            copy(self, module, src_cmake_dir, dst_cmake_dir)

        debugbreak_src_dir = os.path.join(
            self.export_sources_folder, "submodules", "debugbreak"
        )
        if not os.path.isfile(os.path.join(debugbreak_src_dir, "debugbreak.h")):
            raise ConanException("Missing bundled submodule header: debugbreak.h")
        copy(
            self,
            "debugbreak.h",
            debugbreak_src_dir,
            os.path.join(self.source_folder, "src", "c4", "ext", "debugbreak"),
        )
        # Apply both the HarmonyOS CMake portability fix and the OHOS allocator
        # compatibility fix after restoring the release archive's submodules.
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "c4core")
        self.cpp_info.set_property("cmake_target_name", "c4core::c4core")
        self.cpp_info.libs = ["c4core"]
