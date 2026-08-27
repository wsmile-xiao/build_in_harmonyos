#!/usr/bin/env python3
"""Conan recipe for vulkan-tools 1.3.290.

Vulkan Development Tools — vulkaninfo + Mock ICD.
Builds vulkan-headers and volk from source as internal build dependencies,
since neither is published to the Conan registry as a CMake-config provider.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class VulkanToolsConan(ConanFile):
    name = "vulkan-tools"
    version = "1.3.290"
    description = "Vulkan Development Tools including vulkaninfo and Mock ICD"
    license = "Apache-2.0"
    homepage = "https://github.com/KhronosGroup/Vulkan-Tools"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # HarmonyOS: CMake doesn't recognise the platform natively; use Linux
        # compatibility (same kernel, same ABI).
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Disable cube demo — requires X11/Wayland WSI (not available on OHOS).
        tc.variables["BUILD_CUBE"] = "OFF"
        # Disable all Window System Integration (no X11/Wayland/DirectFB).
        tc.variables["BUILD_WSI_XCB_SUPPORT"] = "OFF"
        tc.variables["BUILD_WSI_XLIB_SUPPORT"] = "OFF"
        tc.variables["BUILD_WSI_WAYLAND_SUPPORT"] = "OFF"
        tc.variables["BUILD_WSI_DIRECTFB_SUPPORT"] = "OFF"
        # Install Mock ICD (disabled by default upstream).
        tc.variables["INSTALL_ICD"] = "ON"
        tc.generate()

    def build(self):
        deps_prefix = os.path.join(self.build_folder, "deps-install")

        # R33: Get compiler paths from Conan conf, not shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", check_type=dict) or {}
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")

        # --- Step 1: Build and install vulkan-headers from source ---
        # vulkan-headers is a header-only package (CMake install copies headers
        # and generates VulkanHeadersConfig.cmake).  Not published to the Conan
        # registry with proper cmake_file_name, so we build from source.
        vh_src = os.path.join(self.build_folder, "vulkan-headers-src")
        os.makedirs(vh_src, exist_ok=True)
        get(self, **self.conan_data["vulkan_headers_source"],
            destination=vh_src, strip_root=True)
        vh_build = os.path.join(vh_src, "build-dir")
        self.run(
            f'cmake -S "{vh_src}" -B "{vh_build}" '
            f'-DCMAKE_C_COMPILER="{cc}" '
            f'-DCMAKE_CXX_COMPILER="{cxx}" '
            f'-DCMAKE_INSTALL_PREFIX="{deps_prefix}" '
            f'-DCMAKE_BUILD_TYPE=Release '
            f'-DVULKAN_HEADERS_ENABLE_TESTS=OFF'
        )
        self.run(f'cmake --build "{vh_build}" --target install')

        # --- Step 2: Build and install volk from source ---
        # volk is a small static C library (volk.h + volk.c).  Not published to
        # the Conan registry at all, so we build from source.
        volk_src = os.path.join(self.build_folder, "volk-src")
        os.makedirs(volk_src, exist_ok=True)
        get(self, **self.conan_data["volk_source"],
            destination=volk_src, strip_root=True)
        volk_build = os.path.join(volk_src, "build-dir")
        self.run(
            f'cmake -S "{volk_src}" -B "{volk_build}" '
            f'-DCMAKE_C_COMPILER="{cc}" '
            f'-DCMAKE_CXX_COMPILER="{cxx}" '
            f'-DCMAKE_INSTALL_PREFIX="{deps_prefix}" '
            f'-DCMAKE_BUILD_TYPE=Release '
            f'-DVOLK_INSTALL=ON '
            f'-DVOLK_PULL_IN_VULKAN=OFF'
        )
        self.run(f'cmake --build "{volk_build}" --target install')

        # --- Step 3: Build vulkan-tools ---
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_PREFIX_PATH": deps_prefix})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # Copy license
        copy(self, "LICENSE.txt", dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder, keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.resdirs = ["share/vulkan/icd.d"]
        # Mock ICD shared library
        self.cpp_info.libs = ["VkICD_mock_icd"]
        self.cpp_info.set_property("cmake_file_name", "vulkan-tools")
        self.cpp_info.set_property("cmake_target_name", "vulkan-tools::vulkan-tools")
