#!/usr/bin/env python3
"""Conan recipe — spirv-llvm-translator 20.1.0 (cmake, 鸿蒙 PC 真机原生编译)

LLVM IR <-> SPIR-V 翻译器，依赖 llvm/20.1.0。
构建产物: libLLVMSPIRVLib.a (静态库) + llvm-spirv (可执行工具)
"""
import os
import glob
import shlex

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import check_min_cppstd


class SpirvLlvmTranslatorConan(ConanFile):
    name = "spirv-llvm-translator"
    version = "20.1.0"
    description = "LLVM-based translator for SPIR-V (LLVM IR <-> SPIR-V)"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://github.com/KhronosGroup/SPIRV-LLVM-Translator"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("llvm/20.1.0")

    def validate(self):
        check_min_cppstd(self, 17)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Download SPIRV-Headers at the specific commit required by this version
        # (spirv-headers-tag.conf specifies commit 2b2e05e088841c63c0b6fd4c9fb380d8688738d3)
        spirv_headers = self.conan_data["spirv_headers"]
        get(self, **spirv_headers, strip_root=True,
            destination=os.path.join(self.source_folder, "external", "SPIRV-Headers"))

    def generate(self):
        tc = CMakeToolchain(self)
        # Provide Platform/HarmonyOS.cmake to fix HandleLLVMOptions.cmake platform detection
        # (HarmonyOS uses Linux kernel; Platform/Linux sets UNIX=1 which LLVM expects)
        if self.settings.os == "OHOS":
            pm = os.path.join(self.build_folder, "_cmake_modules")
            os.makedirs(os.path.join(pm, "Platform"), exist_ok=True)
            with open(os.path.join(pm, "Platform", "HarmonyOS.cmake"), "w", encoding="utf-8") as f:
                f.write("include(Platform/Linux)\n")
            tc.cache_variables["CMAKE_MODULE_PATH"] = pm
        # Skip FetchContent for SPIRV-Headers (use local copy downloaded in source())
        tc.cache_variables["LLVM_EXTERNAL_SPIRV_HEADERS_SOURCE_DIR"] = os.path.join(
            self.source_folder, "external", "SPIRV-Headers")
        tc.cache_variables["LLVM_SPIRV_INCLUDE_TESTS"] = "OFF"
        tc.cache_variables["LLVM_SPIRV_BUILD_EXTERNAL"] = "YES"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self.run("ctest --output-on-failure", cwd=self.build_folder, ignore_errors=True)

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_elf_files(self, folder):
        """Sign ELF binaries for OHOS XPM (required for execution on device)."""
        targets = glob.glob(os.path.join(folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = os.environ.get("LLVM_OBJCOPY", "llvm-objcopy")
        signer = os.environ.get("BINARY_SIGN_TOOL", "binary-sign-tool")
        for f in targets:
            if os.path.islink(f):
                continue
            # Remove existing .codesign section (may not exist, ignore errors)
            self.run(f"{shlex.quote(objcopy)} --remove-section .codesign {shlex.quote(f)}", ignore_errors=True)
            # Sign the binary; non-fatal in CI (binary-sign-tool may not be installed)
            self.run(f"{shlex.quote(signer)} sign -inFile {shlex.quote(f)} -outFile {shlex.quote(f)} -selfSign 1", ignore_errors=True)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if self.settings.os == "OHOS":
            self._sign_elf_files(self.package_folder)

    def package_info(self):
        self.cpp_info.libs = ["LLVMSPIRVLib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
