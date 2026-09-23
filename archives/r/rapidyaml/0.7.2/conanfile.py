#!/usr/bin/env python3
"""Conan recipe for rapidyaml 0.7.2 — CMake library (static, HarmonyOS/PC).

rapidyaml vendors c4core as a git submodule pinned at c4core v0.2.2; the
official GitHub source tarball does NOT include submodule contents, so this
recipe downloads the official c4core v0.2.2 tarball, extracts it into
ext/c4core, restores the biojppm/cmake modules (vendored under patches/) and
the debugbreak submodule header, then applies the HarmonyOS platform fix and
the CMake >= 4.0 CMP0037 guard to c4Project.cmake before building.
"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.errors import ConanInvalidConfiguration


class RapidYAMLConan(ConanFile):
    name = "rapidyaml"
    version = "0.7.2"
    description = "a library to parse and emit YAML, and do it fast"
    topics = ("yaml", "parser", "emitter")
    url = "https://github.com/biojppm/rapidyaml"
    homepage = "https://github.com/biojppm/rapidyaml"
    license = "MIT"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # biojppm/cmake modules vendored from the c4core submodule
    # (c4core's cmake/ submodule is empty in the official source tarball).
    _C4CORE_CMAKE_MODULES = (
        "ConfigurationTypes.cmake",
        "CreateSourceGroup.cmake",
        "ExternalProjectUtils.cmake",
        "FindD3D12.cmake",
        "FindDX12.cmake",
        "GetFlags.cmake",
        "GetNames.cmake",
        "PVS-Studio.cmake",
        "PatchUtils.cmake",
        "PrintVar.cmake",
        "TargetArchitecture.cmake",
        "Toolchain-Arm-ubuntu.cmake",
        "Toolchain-Armv7.cmake",
        "Toolchain-PS4.cmake",
        "Toolchain-XBoxOne.cmake",
        "c4CatSources.cmake",
        "c4Doxygen.cmake",
        "c4DoxygenConfig.cmake",
        "c4GetTargetPropertyRecursive.cmake",
        "c4Project.cmake",
        "c4StaticAnalysis.cmake",
        "c4stlAddTarget.cmake",
    )

    def export_sources(self):
        export_conandata_patches(self)
        # Vendored c4core submodule contents: biojppm/cmake modules + debugbreak.h
        pdir = os.path.join(self.recipe_folder, "patches")
        edir = os.path.join(self.export_sources_folder, "patches")
        for module in self._C4CORE_CMAKE_MODULES:
            copy(self, module, pdir, edir)
        copy(
            self,
            "debugbreak.h",
            os.path.join(pdir, "submodules", "debugbreak"),
            os.path.join(edir, "submodules", "debugbreak"),
        )

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.shared

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("rapidyaml is supported only on Linux/OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Official c4core submodule (pinned v0.2.2 by upstream v0.7.2)
        c4core_cfg = self.conan_data["c4core_sources"]["0.2.2"]
        c4core_tmp = os.path.join(self.source_folder, ".c4core_dl")
        os.makedirs(c4core_tmp, exist_ok=True)
        get(self, **c4core_cfg, destination=c4core_tmp, strip_root=True)
        # strip_root=True unpacks c4core's contents directly into c4core_tmp
        ext_c4core = os.path.join(self.source_folder, "ext", "c4core")
        if os.path.isdir(ext_c4core):
            shutil.rmtree(ext_c4core)
        os.rename(c4core_tmp, ext_c4core)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["RYML_INSTALL"] = True
        tc.variables["RYML_BUILD_TOOLS"] = False
        tc.variables["RYML_BUILD_API"] = False
        tc.variables["RYML_BUILD_BENCHMARKS"] = False
        tc.variables["RYML_BUILD_TESTS"] = False
        tc.variables["C4CORE_WITH_FASTFLOAT"] = True
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        # Restore c4core's vendored cmake/ submodule contents (empty in tarball)
        src_cmake = os.path.join(self.export_sources_folder, "patches")
        dst_cmake = os.path.join(self.source_folder, "ext", "c4core", "cmake")
        os.makedirs(dst_cmake, exist_ok=True)
        for module in self._C4CORE_CMAKE_MODULES:
            copy(self, module, src_cmake, dst_cmake)
        # Restore c4core's vendored debugbreak submodule header
        dbg_src = os.path.join(self.export_sources_folder, "patches", "submodules", "debugbreak")
        dbg_dst = os.path.join(
            self.source_folder, "ext", "c4core", "src", "c4", "ext", "debugbreak"
        )
        os.makedirs(dbg_dst, exist_ok=True)
        copy(self, "debugbreak.h", dbg_src, dbg_dst)

        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"] if self.conf.get("tools.build:jobs", default=1) == 1 else [])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ryml")
        self.cpp_info.set_property("cmake_target_name", "ryml::ryml")
        self.cpp_info.libs = ["ryml"]
        # ryml headers include <c4/...> (c4core) transitively; the static lib
        # is self-contained (c4core compiled in), but consumers need c4core
        # headers which are installed into include/ alongside ryml's.
        self.cpp_info.includedirs = ["include"]
