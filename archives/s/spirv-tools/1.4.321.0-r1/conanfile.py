#!/usr/bin/env python3
"""Conan recipe for SPIRV-Tools 1.4.321.0-r1."""
import os
import shutil
import tarfile
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches, get


class SpirvToolsConan(ConanFile):
    name = "spirv-tools"
    version = "1.4.321.0-r1"
    description = "SPIR-V processing library and command line tools"
    license = "Apache-2.0"
    homepage = "https://github.com/KhronosGroup/SPIRV-Tools"
    url = ""
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._extract_spirv_headers()

    def _extract_spirv_headers(self):
        headers = self.conan_data["resources"]["spirv_headers"]
        archive_path = os.path.join(self.source_folder, "spirv-headers.tar.gz")
        download(self, url=headers["url"], filename=archive_path, sha256=headers["sha256"])
        try:
            with tempfile.TemporaryDirectory(dir=self.source_folder) as tmp_extract:
                with tarfile.open(archive_path, "r:gz") as archive:
                    archive.extractall(tmp_extract)
                roots = [
                    os.path.join(tmp_extract, name)
                    for name in os.listdir(tmp_extract)
                ]
                roots = [path for path in roots if os.path.isdir(path)]
                if len(roots) != 1:
                    raise ConanInvalidConfiguration(
                        "Unexpected SPIRV-Headers archive layout"
                    )
                dst = os.path.join(
                    self.source_folder, "external", "spirv-headers"
                )
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                shutil.move(roots[0], dst)
        finally:
            if os.path.isfile(archive_path):
                os.unlink(archive_path)

    def generate(self):
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["SPIRV_TOOLS_BUILD_STATIC"] = not bool(self.options.shared)
        tc.cache_variables["SPIRV_SKIP_EXECUTABLES"] = "ON"
        tc.cache_variables["SPIRV_SKIP_TESTS"] = "ON"
        tc.cache_variables["SPIRV_WERROR"] = "OFF"
        tc.cache_variables["SPIRV_COLOR_TERMINAL"] = "OFF"
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = [
            "SPIRV-Tools-opt",
            "SPIRV-Tools-link",
            "SPIRV-Tools-lint",
            "SPIRV-Tools-reduce",
            "SPIRV-Tools-diff",
            "SPIRV-Tools",
        ]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.system_libs = ["pthread"]
