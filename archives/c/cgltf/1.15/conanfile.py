#!/usr/bin/env python3
"""Conan recipe for cgltf 1.15.

cgltf is a single-file C99 glTF 2.0 parser/loader (cgltf.h + cgltf_write.h).
Upstream test/CMakeLists.txt hard-codes -fsanitize=address and -Werror which
OHOS clang rejects; we patch those out and compile the four self-contained
upstream test suites in build().
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CgltfConan(ConanFile):
    name = "cgltf"
    version = "1.15"
    description = "Single-file C99 glTF 2.0 parser/loader"
    license = "MIT"
    homepage = "https://github.com/jkuhlmann/cgltf"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/c/cgltf/1.15"
    topics = ("gltf", "parser", "c99", "single-header")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False], "run_upstream_tests": [True, False]}
    default_options = {"shared": False, "fPIC": True, "run_upstream_tests": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos", "FreeBSD"):
            raise ConanInvalidConfiguration(f"{self.name} not validated for {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = exes.get("c") or "clang"
        ar = exes.get("ar") or "llvm-ar"
        sf = self.source_folder
        opt = "-O2" if str(self.settings.build_type) != "Debug" else "-O0 -g"
        fpic = "-fPIC" if self.options.get_safe("fPIC", True) else ""

        impl_src = os.path.join(self.build_folder, "cgltf_impl.c")
        with open(impl_src, "w") as f:
            f.write('#define CGLTF_IMPLEMENTATION\n#include "cgltf.h"\n')

        obj = os.path.join(self.build_folder, "cgltf.o")
        lib = os.path.join(self.build_folder, "libcgltf.a")
        self.run(f'"{cc}" {opt} {fpic} -std=c99 -I"{sf}" -c "{impl_src}" -o "{obj}"', env="conanbuild")
        self.run(f'"{ar}" rcs "{lib}" "{obj}"', env="conanbuild")

        if self.options.run_upstream_tests and can_run(self):
            cxx = exes.get("cpp") or "clang++"
            tp = os.path.join(sf, "test")
            flags = f'-std=c++11 {opt} -I"{sf}"'
            suites = ["test_math.cpp", "test_strings.cpp"]
            for src in suites:
                out = os.path.join(self.build_folder, src.replace(".cpp", ""))
                self.output.info(f"Compiling upstream test {src}")
                self.run(f'"{cxx}" {flags} "{os.path.join(tp, src)}" "{lib}" -o "{out}"', env="conanbuild")
                self.output.info(f"Running upstream test {src}")
                self.run(f'"{out}"', env="conanbuild")

    def package(self):
        copy(self, "cgltf.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "cgltf_write.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["cgltf"]
        self.cpp_info.set_property("cmake_target_name", "cgltf::cgltf")
