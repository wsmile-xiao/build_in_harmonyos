#!/usr/bin/env python3
"""Conan recipe for libnfs-tools 5.0.3.

libnfs-tools is the command-line tool set (nfs-ls/nfs-cat/nfs-cp/nfs-stat)
that upstream libnfs ships in its utils/ directory.  Upstream has no
separate "libnfs-tools" repository: the four utilities are part of the
official libnfs tarball (tag libnfs-5.0.3) and are packaged here as an
independent CLI package that links against the published libnfs/5.0.3
library (declared in requires, R36 dependency-first).

HarmonyOS PC / aarch64 build notes
----------------------------------
* Only utils/{nfs-cat,nfs-ls,nfs-cp,nfs-stat}.c are compiled; the whole
  libnfs library comes from the conan dependency libnfs/5.0.3 (static).
* A tiny generated CMakeLists.txt (ohos-build/) is used to keep the build
  reproducible in CI (R33: toolchain/compiler flags come from Conan, never
  bare shell vars).  libnfs is consumed via CMakeDeps target libnfs::nfs.
* HAVE_UNISTD_H / HAVE_POLL_H are defined because the tools use autotools
  config.h feature macros and we do not run configure for this package.
* R38: this package is a CLI tool set, commands.json is declared at the
  software level (archives/l/libnfs-tools/commands.json).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


CMAKE_LISTS_TEMPLATE = r"""
cmake_minimum_required(VERSION 3.15)
project(libnfs-tools C)

find_package(libnfs CONFIG REQUIRED)

get_target_property(_LIBNFS_INC libnfs::nfs INTERFACE_INCLUDE_DIRECTORIES)

set(UTILS_DIR "{src_root}/utils")
set(UTILITIES nfs-cat nfs-ls nfs-cp nfs-stat)

foreach(T ${{UTILITIES}})
  add_executable(${{T}} ${{UTILS_DIR}}/${{T}}.c)
  target_link_libraries(${{T}} PRIVATE libnfs::nfs)
  # libnfs public headers live under <include>/nfsc; the tools include them
  # with quotes ("libnfs.h") and as <nfsc/libnfs-raw.h>, so both the root
  # and nfsc/ dirs are needed on the include path.
  target_include_directories(${{T}} PRIVATE ${{_LIBNFS_INC}} ${{_LIBNFS_INC}}/nfsc)
  target_compile_definitions(${{T}} PRIVATE HAVE_UNISTD_H=1 HAVE_POLL_H=1)
endforeach()

install(TARGETS ${{UTILITIES}} RUNTIME DESTINATION bin)
"""


class LibnfsToolsConan(ConanFile):
    name = "libnfs-tools"
    version = "5.0.3"
    description = ("Command-line tools (nfs-ls/nfs-cat/nfs-cp/nfs-stat) "
                   "for accessing NFS shares")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/sahlberg/libnfs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libnfs/5.0.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Generate a small standalone CMakeLists.txt that compiles only the
        # four utilities against the conan-provided libnfs.  It lives under
        # source_folder/ohos-build so conan's CMake helper can find it.
        src_root = self.source_folder
        build_dir = os.path.join(src_root, "ohos-build")
        os.makedirs(build_dir, exist_ok=True)
        cmake_lists = CMAKE_LISTS_TEMPLATE.format(src_root=src_root)
        cmake_lists_path = os.path.join(build_dir, "CMakeLists.txt")
        with open(cmake_lists_path, "w", encoding="utf-8") as fh:
            fh.write(cmake_lists)
        cmake = CMake(self)
        cmake.configure(build_script_folder="ohos-build")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # R38: CLI tools, no library components
        self.cpp_info.libs = []
