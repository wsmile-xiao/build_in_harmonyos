#!/usr/bin/env python3
"""Conan recipe — nvtop 3.3.2 (htop-like GPU process monitor).

nvtop 是 Syllo/nvtop 的官方名称，仓库地址: https://github.com/Syllo/nvtop
构建系统：CMake
平台：OHOS / Linux
依赖：ncurses（终端界面）
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file, save
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class NvtopConan(ConanFile):
    name = "nvtop"
    version = "3.3.2"
    description = "nvtop — htop-like GPU process monitor for NVIDIA, AMD, Intel, Apple, Mali and other GPUs"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/Syllo/nvtop"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"nvtop supports Linux/OHOS only, not {self.settings.os}"
            )

    def requirements(self):
        # OHOS needs ncurses from Conan for terminal UI
        # Use generic reference (no user/channel) — ohpcd remote auto-resolves
        # uploaded binaries with @ohpcd/stable.
        self.requires("ncurses/6.5")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Disable all GPU vendor support on OHOS — only the ncurses TUI and Linux
        # process monitoring code is useful; NVIDIA/AMD/Intel/Mali driver stacks
        # are not present on OHOS.
        tc.variables["NVIDIA_SUPPORT"] = "OFF"
        tc.variables["AMDGPU_SUPPORT"] = "OFF"
        tc.variables["INTEL_SUPPORT"] = "OFF"
        tc.variables["APPLE_SUPPORT"] = "OFF"
        tc.variables["MSM_SUPPORT"] = "OFF"
        tc.variables["PANFROST_SUPPORT"] = "OFF"
        tc.variables["PANTHOR_SUPPORT"] = "OFF"
        tc.variables["ASCEND_SUPPORT"] = "OFF"
        tc.variables["V3D_SUPPORT"] = "OFF"
        tc.variables["TPU_SUPPORT"] = "OFF"
        tc.variables["ROCKCHIP_SUPPORT"] = "OFF"
        tc.variables["METAX_SUPPORT"] = "OFF"
        tc.variables["ENFLAME_SUPPORT"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # OHOS/HarmonyOS is Linux-compatible but CMake treats it as unknown platform,
        # causing UNIX=FALSE which drops Linux-specific source files from nvtop.
        # Patch CMakeLists.txt to recognize HarmonyOS as a UNIX-like system.
        cmake_lists = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        replace_in_file(self, cmake_lists,
                       "if(UNIX AND NOT APPLE)",
                       "if((UNIX AND NOT APPLE) OR CMAKE_SYSTEM_NAME STREQUAL \"HarmonyOS\")")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Binary is named nvtop upstream — keep as-is.
        src_bin = os.path.join(self.package_folder, "bin", "nvtop")

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.define_path("PATH", os.path.join(self.package_folder, "bin"))
