#!/usr/bin/env python3
"""Conan recipe for scudo-malloc 19.1.6 (LLVM compiler-rt scudo standalone allocator).

scudo-malloc is the SCUDO (Sanitizer Combined Allocator) standalone memory
allocator from LLVM's compiler-rt project. It provides hardened memory allocation
with protections against heap overflow, double-free, and use-after-free.

Uses individual LLVM source packages (compiler-rt + cmake + llvm) instead of
the full 141MB llvm-project source for faster downloads.
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ScudoMallocConan(ConanFile):
    name = "scudo-malloc"
    version = "19.1.6"
    description = "SCUDO standalone memory allocator from LLVM compiler-rt"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://llvm.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        src = self.conan_data["sources"]
        # Download and extract compiler-rt source
        get(self, url=src["compiler-rt"]["url"], sha256=src["compiler-rt"]["sha256"], strip_root=True)
        os.makedirs("compiler-rt", exist_ok=True)
        for item in os.listdir("."):
            if item != "compiler-rt" and not item.startswith("."):
                shutil.move(item, os.path.join("compiler-rt", item))
        # Download and extract common cmake modules
        get(self, url=src["cmake"]["url"], sha256=src["cmake"]["sha256"], strip_root=True)
        os.makedirs("cmake", exist_ok=True)
        for item in os.listdir("."):
            if item not in ("compiler-rt", "cmake") and not item.startswith("."):
                shutil.move(item, os.path.join("cmake", item))
        # Download and extract llvm source (needed for llvm/cmake/modules/AddLLVM.cmake)
        get(self, url=src["llvm"]["url"], sha256=src["llvm"]["sha256"], strip_root=True)
        os.makedirs("llvm", exist_ok=True)
        for item in os.listdir("."):
            if item not in ("compiler-rt", "cmake", "llvm") and not item.startswith("."):
                shutil.move(item, os.path.join("llvm", item))

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.variables["COMPILER_RT_BUILD_SANITIZERS"] = "ON"
        tc.variables["COMPILER_RT_SANITIZERS_TO_BUILD"] = "scudo_standalone"
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["COMPILER_RT_BUILD_XRAY"] = "OFF"
        tc.variables["COMPILER_RT_BUILD_LIBFUZZER"] = "OFF"
        tc.variables["COMPILER_RT_BUILD_PROFILE"] = "OFF"
        tc.variables["COMPILER_RT_BUILD_BUILTINS"] = "OFF"
        tc.variables["COMPILER_RT_BUILD_ORC"] = "OFF"
        tc.variables["COMPILER_RT_BUILD_MEMPROF"] = "OFF"
        tc.variables["COMPILER_RT_BUILD_CTX_PROFILE"] = "OFF"
        tc.variables["COMPILER_RT_BUILD_GWP_ASAN"] = "OFF"
        # LLVM_MAIN_SRC_DIR is used by compiler-rt's mock to find llvm/cmake/modules/
        tc.variables["LLVM_MAIN_SRC_DIR"] = self.source_folder
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "compiler-rt"))
        cmake.build(target="scudo_standalone")

    def package(self):
        build_dir = os.path.join(self.build_folder, "lib", "linux")
        for f in glob.glob(os.path.join(build_dir, "*.a")):
            copy(self, os.path.basename(f), build_dir, os.path.join(self.package_folder, "lib"))
        for f in glob.glob(os.path.join(build_dir, "*.so")):
            copy(self, os.path.basename(f), build_dir, os.path.join(self.package_folder, "lib"))
        include_dir = os.path.join(self.source_folder, "compiler-rt", "include")
        copy(self, "*.h", include_dir, os.path.join(self.package_folder, "include"))

    def package_info(self):
        arch_map = {"armv8": "aarch64", "x86_64": "x86_64"}
        arch = arch_map.get(str(self.settings.arch), str(self.settings.arch))
        if self.options.shared:
            self.cpp_info.libs = [f"clang_rt.scudo_standalone-{arch}"]
        else:
            self.cpp_info.libs = [
                f"clang_rt.scudo_standalone-{arch}",
                f"clang_rt.scudo_standalone_cxx-{arch}",
            ]
        self.cpp_info.includedirs = ["include"]
