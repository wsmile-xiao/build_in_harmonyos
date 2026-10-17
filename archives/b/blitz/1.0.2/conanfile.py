import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    rmdir,
)


class BlitzConan(ConanFile):
    name = "blitz"
    version = "1.0.2"
    description = "Blitz++ multi-dimensional array and numeric expression template library"
    license = "Artistic-2.0 OR BSD-3-Clause OR LGPL-3.0-or-later"
    homepage = "https://github.com/blitzpp/blitz"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_DOC"] = "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BLITZ_BUILD_SHARED"] = "OFF"
        tc.variables["BLITZ_BUILD_EXAMPLES"] = "OFF"
        tc.variables["BLITZ_BUILD_BENCHMARKS"] = "OFF"
        tc.variables["ENABLE_SERIALISATION"] = "OFF"
        tc.variables["TBB"] = "OFF"
        tc.variables["SIMD_EXTENSION"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"])
        cmake.build(target="testsuite", cli_args=["--parallel", "1"])
        if can_run(self):
            self.run(
                "ctest --output-on-failure --no-tests=error",
                cwd=self.build_folder,
                env="conanbuild",
            )
        else:
            self.output.info("Skipping blitz upstream tests: target binaries cannot run here")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYRIGHT", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.LESSER", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        rm(self, "libblitz.so*", os.path.join(self.package_folder, "lib"))
        rm(self, "libblitz.dylib*", os.path.join(self.package_folder, "lib"))
        rm(self, "blitz.dll", os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["blitz"]
        self.cpp_info.set_property("cmake_file_name", "blitz")
        self.cpp_info.set_property("cmake_target_name", "blitz::blitz")
        self.cpp_info.bindirs = []
        if str(self.settings.os) not in ("Windows",):
            self.cpp_info.system_libs.append("m")
