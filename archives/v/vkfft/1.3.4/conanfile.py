#!/usr/bin/env python3
"""Conan recipe — vkfft 1.3.4 (header-only FFT library).

VkFFT is a header-only GPU FFT library (Vulkan / CUDA / HIP / OpenCL /
Level Zero / Metal backends selected via the VKFFT_BACKEND macro).
This recipe packages the full `vkFFT/` header tree for the Vulkan
backend (VKFFT_BACKEND=0, the upstream default):

  include/vkFFT/vkFFT.h            — public entry header
  include/vkFFT/vkFFT/**           — internal header subtree
  include/glslang_c_interface.h    — shim: upstream consumers get this
                                     header flat (upstream CMake adds
                                     glslang's <prefix>/glslang/Include/
                                     to the include path); our glslang
                                     dependency installs it under
                                     glslang/Include/, so the shim
                                     forwards to it without patching
                                     upstream sources.

Consumers compile with -DVKFFT_BACKEND=0 (or leave it, it defaults to
0 in vkFFT.h) and `#include <vkFFT/vkFFT.h>`.

Dependencies (already published to the ohpcd registry, R36):
  - vulkan-headers/vulkan-sdk-1.4.357.0  — vulkan/vulkan.h types
  - glslang/vulkan-sdk-1.3.290.0         — glslang_c_interface.h + SPIR-V
                                           runtime used by vkFFT to
                                           compile shaders at runtime
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class VkfftConan(ConanFile):
    name = "vkfft"
    version = "1.3.4"
    description = "VkFFT — GPU-accelerated Fast Fourier Transform library (header-only, Vulkan backend)"
    license = "MIT"
    homepage = "https://github.com/DTolm/VkFFT"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "header-library"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # visible=True: vulkan-headers' recipe declares package_type
        # "build-scripts", which makes Conan auto-hide it (visible=False);
        # vkfft.h consumers DO need its include dirs, so force visibility.
        self.requires("vulkan-headers/vulkan-sdk-1.4.357.0", visible=True)
        self.requires("glslang/vulkan-sdk-1.3.290.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only: nothing to compile. Validate the header tree exists.
        apply_conandata_patches(self)
        src = os.path.join(self.source_folder, "vkFFT")
        if not os.path.isfile(os.path.join(src, "vkFFT.h")):
            raise ConanException(f"vkFFT.h missing under {src}")

    def package(self):
        src = os.path.join(self.source_folder, "vkFFT")
        # Preserve the upstream include convention: consumers do
        # #include <vkFFT/vkFFT.h>, internal headers do
        # #include "vkFFT/vkFFT_Structs/..." (needs the parent of the
        # inner vkFFT/ subtree on the include path — see package_info).
        shutil.copytree(src, os.path.join(self.package_folder, "include", "vkFFT"))
        inc = os.path.join(self.package_folder, "include")
        if not os.path.isfile(os.path.join(inc, "vkFFT", "vkFFT.h")):
            raise ConanException("packaged vkFFT/vkFFT.h missing")
        # glslang C-interface shim (see module docstring)
        with open(os.path.join(inc, "glslang_c_interface.h"), "w") as f:
            f.write(
                "#ifndef VKFFT_GLSLANG_C_INTERFACE_SHIM_H\n"
                "#define VKFFT_GLSLANG_C_INTERFACE_SHIM_H\n"
                "#include <glslang/Include/glslang_c_interface.h>\n"
                "#endif\n")
        # licenses
        lic_src = os.path.join(self.source_folder, "LICENSE")
        if os.path.isfile(lic_src):
            lic_dir = os.path.join(self.package_folder, "licenses")
            os.makedirs(lic_dir, exist_ok=True)
            shutil.copy(lic_src, os.path.join(lic_dir, "LICENSE"))

    def package_info(self):
        inc = os.path.join(self.package_folder, "include")
        self.cpp_info.includedirs = ["include", os.path.join("include", "vkFFT")]
        self.cpp_info.requires = [
            "vulkan-headers::vulkan-headers",
            "glslang::glslang",
        ]
        self.cpp_info.set_property("cmake_file_name", "VkFFT")
        self.cpp_info.set_property("cmake_target_name", "VkFFT::VkFFT")
        self.output.info(f"vkFFT header-only package, include root: {inc}")
