#!/usr/bin/env python3
"""Conan recipe for xdelta3 — VCDIFF (RFC 3284) delta compression library and tool.

Build system: CMake (>= 3.13), C99/C++11.
Products: xdelta3 CLI tool + libxdelta3 static library + auxiliary tools.
License: Apache License 2.0.

Enforced rules:
  R32: settings.os in ("Linux", "OHOS")
  R33: All compiler/flags from Conan Toolchain, no bare shell variables
  R34: test_package calls xd3_encode_memory / xd3_decode_memory (real API)
  R38: commands.json declares the xdelta3 CLI at software-level directory
  R39: Source URL is official GitHub release
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file


class Xdelta3Conan(ConanFile):
    name = "xdelta3"
    version = "3.2.0"
    description = "VCDIFF (RFC 3284) delta compression library and tool"
    license = "Apache-2.0"
    homepage = "https://github.com/jmacd/xdelta"
    url = "https://github.com/jmacd/xdelta"

    # The CMake build hardcodes add_library(xdelta3lib STATIC ...),
    # so only static library is supported.
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # xz provides liblzma for LZMA secondary compression
        self.requires("xz/5.6.2")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32: settings.os must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "xdelta3 only supports Linux and OHOS"
            )

    def source(self):
        # strip_root=True strips the top-level xdelta-3.2.0/ directory.
        # The actual source is in the xdelta3/ subdirectory.
        get(self, **self.conan_data["sources"], strip_root=True)

        # Move xdelta3/ subdirectory contents to the source root
        # so CMakeLists.txt is at the top level.
        xdelta3_dir = os.path.join(self.source_folder, "xdelta3")
        if os.path.isdir(xdelta3_dir):
            for item in os.listdir(xdelta3_dir):
                src_path = os.path.join(xdelta3_dir, item)
                dst_path = os.path.join(self.source_folder, item)
                if os.path.exists(dst_path):
                    if os.path.isdir(dst_path):
                        shutil.rmtree(dst_path)
                    else:
                        os.remove(dst_path)
                shutil.move(src_path, dst_path)
            os.rmdir(xdelta3_dir)

        # Patch CMakeLists.txt: the upstream uses find_package(LibLZMA) but
        # the Conan xz package generates find_package(xz) / xz::xz target.
        # Add a Conan-first lookup that falls back to the original logic.
        cmake_file = os.path.join(self.source_folder, "CMakeLists.txt")
        replace_in_file(self, cmake_file,
            "  find_package(LibLZMA)\n"
            "  if(LibLZMA_FOUND)\n"
            "    set(HAVE_LZMA_H ON)\n"
            "    set(XD3_LZMA_LIBRARIES LibLZMA::LibLZMA)\n"
            "  else()",
            "  # Conan CMakeDeps: xz package generates find_package(xz)\n"
            "  find_package(xz CONFIG QUIET)\n"
            "  if(TARGET xz::xz)\n"
            "    set(HAVE_LZMA_H ON)\n"
            "    set(XD3_LZMA_LIBRARIES xz::xz)\n"
            "  else()\n"
            "    find_package(LibLZMA)\n"
            "    if(LibLZMA_FOUND)\n"
            "      set(HAVE_LZMA_H ON)\n"
            "      set(XD3_LZMA_LIBRARIES LibLZMA::LibLZMA)\n"
            "    else()")
        # Close the extra else() block we introduced
        replace_in_file(self, cmake_file,
            "    endif()\n"
            "  endif()\n"
            "  if(NOT HAVE_LZMA_H AND XD3_LZMA_MODE STREQUAL \"on\")",
            "    endif()\n"
            "  endif()\n"
            "  endif()\n"
            "  if(NOT HAVE_LZMA_H AND XD3_LZMA_MODE STREQUAL \"on\")")

    def generate(self):
        tc = CMakeToolchain(self)
        # Disable armor mode: BLAKE3 is fetched via FetchContent from GitHub,
        # which is not accessible in the CI/offline build environment.
        tc.variables["XD3_ARMOR"] = False
        # Enable LZMA secondary compression using the Conan xz dependency.
        # CMakeDeps will provide find_package(xz) / xz::xz target.
        tc.variables["XD3_LZMA_MODE"] = "auto"
        # Build the reusable xdelta3 core library (XD3_MAIN=0).
        tc.variables["XD3_BUILD_LIB"] = True
        # Disable regression-test executables in the Conan build;
        # test_package handles consumer-side testing.
        tc.variables["XD3_BUILD_TESTS"] = False
        tc.generate()
        # Generate CMakeDeps for the xz dependency
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "xdelta3")
        self.cpp_info.set_property("cmake_target_name", "xdelta3::xdelta3")
        self.cpp_info.set_property("pkg_config_name", "xdelta3")
        self.cpp_info.libs = ["xdelta3"]
        # Executables (xdelta3 CLI tool) are installed to bin/
        self.cpp_info.bindirs = ["bin"]
        # ABI defines required by consumers including xdelta3.h.
        # The upstream CMake sets these via INTERFACE_COMPILE_DEFINITIONS on
        # the xdelta3lib target, but Conan CMakeDeps does not propagate
        # them from the installed CMake config.  Without these, xdelta3.h
        # fails to typedef usize_t/xoff_t (SIZEOF_* all evaluate to 0).
        arch = str(self.settings.arch)
        # Detect 64-bit architectures: most 64-bit arch names end with "64"
        # (x86_64, aarch64, riscv64, ppc64, mips64, loongarch64, etc.)
        # ARMv8/v9+ variants (armv8, armv8.3, armv9, ...) are also 64-bit.
        is_64bit = arch.endswith("64") or arch.startswith(("armv8", "armv9"))
        if is_64bit:
            self.cpp_info.defines = [
                "SIZEOF_SIZE_T=8",
                "SIZEOF_UNSIGNED_LONG=8",
                "XD3_USE_LARGESIZET=1",
            ]
        else:
            self.cpp_info.defines = [
                "SIZEOF_SIZE_T=4",
                "SIZEOF_UNSIGNED_LONG=4",
                "XD3_USE_LARGESIZET=0",
            ]
        self.cpp_info.defines.extend([
            "SIZEOF_UNSIGNED_INT=4",
            "SIZEOF_UNSIGNED_LONG_LONG=8",
            "XD3_USE_LARGEFILE64=1",
        ])
