#!/usr/bin/env python3
"""Conan recipe for c3c — the C3 language compiler.

Build: CMake
LLVM: auto-downloaded via C3_FETCH_LLVM=ON (CI), or system-installed (OHOS)
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class C3CConan(ConanFile):
    name = "c3c"
    version = "0.8.1"
    description = "C3 language compiler — an evolution of C"
    license = "LGPL-3.0"
    homepage = "https://c3-lang.org"
    url = "https://github.com/c3lang/c3c"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, url=self.conan_data["sources"]["url"], sha256=self.conan_data["sources"]["sha256"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS SDK has libc++ only. The upstream linux-aarch64 LLVM artifact
        # requires GNU libstdc++, so do not fetch/link it in CI.
        if self.settings.os in ("OHOS",):
            tc.variables["C3_WITH_LLVM"] = "OFF"
            tc.variables["C3_FETCH_LLVM"] = "OFF"
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            # Disable non-AArch64 targets (only AArch64 is relevant for OHOS)
            target_flags = "-DAVR_DISABLE -DARM_DISABLE -DRISCV_DISABLE -DWASM_DISABLE -DX86_DISABLE -Wno-error=switch"
            tc.cache_variables["CMAKE_C_FLAGS"] = target_flags
            tc.cache_variables["CMAKE_CXX_FLAGS"] = target_flags
        else:
            tc.variables["C3_FETCH_LLVM"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # CI: use gh-proxy to download LLVM from GitHub
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
            "https://github.com/c3lang/llvm-for-c3/releases",
            "https://gh-proxy.com/https://github.com/c3lang/llvm-for-c3/releases")
        # CI/OHOS: define the zstd target once for every LLVM discovery path.
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
            '    set(ZLIB_FOUND TRUE CACHE INTERNAL "")\n\n    if(C3_FETCH_LLVM)',
            '''    set(ZLIB_FOUND TRUE CACHE INTERNAL "")

    if(NOT TARGET zstd::libzstd_shared)
        add_library(zstd::libzstd_shared INTERFACE IMPORTED)
    endif()

    if(C3_FETCH_LLVM)''')
        # CI: comment out include_directories(${LLVM_INCLUDE_DIRS}) to avoid
        # /usr/include being added to imported LLVM targets' INTERFACE_INCLUDE_DIRECTORIES
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
            "include_directories(${LLVM_INCLUDE_DIRS})",
            "# include_directories(${LLVM_INCLUDE_DIRS})  # OHOS: moved to target_include_directories")
        # Add LLVM include dirs to c3c and c3c_wrappers targets
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
            'target_include_directories(c3c PRIVATE\n        "${CMAKE_SOURCE_DIR}/src/"\n        "${CMAKE_BINARY_DIR}")',
            'target_include_directories(c3c PRIVATE\n        "${CMAKE_SOURCE_DIR}/src/"\n        "${CMAKE_BINARY_DIR}"\n        ${LLVM_INCLUDE_DIRS})')
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
            'target_include_directories(c3c_wrappers PRIVATE\n            "${CMAKE_SOURCE_DIR}/wrapper/include/")',
            'target_include_directories(c3c_wrappers PRIVATE\n            "${CMAKE_SOURCE_DIR}/wrapper/include/"\n            ${LLVM_INCLUDE_DIRS})')
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        command = os.path.join(self.build_folder, "c3c") + " utest"
        if self.run(command, ignore_errors=True) != 0:
            raise ConanException(f"Upstream compiler self-tests failed: {command}")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "lib/*", src=self.source_folder, dst=os.path.join(self.package_folder, "lib", "c3"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]