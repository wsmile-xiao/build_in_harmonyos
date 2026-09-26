#!/usr/bin/env python3
"""Conan recipe for gflags 2.3.1 (CMake)."""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    download,
    rm,
    unzip,
)


class GflagsConan(ConanFile):
    name = "gflags"
    version = "2.3.1"
    description = "C++ command-line flag declaration and parsing library"
    license = "BSD-3-Clause"
    homepage = "https://gflags.github.io/gflags/"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        os_name = str(self.settings.os)
        if os_name not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("gflags is packaged for Linux/OHOS")
        if os_name == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("gflags supports OHOS armv8 only")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        # Windows is case-insensitive: upstream Bazel file BUILD conflicts with
        # cmake_layout()'s default build/ directory.
        self.folders.source = "."
        self.folders.build = "conan-build"
        self.folders.generators = os.path.join(self.folders.build, "generators")

    def source(self):
        sources = self.conan_data["sources"]
        archive = "gflags-2.3.1.tar.gz"
        download(
            self,
            url=sources["url"],
            filename=archive,
            sha256=sources["sha256"],
        )
        unzip(self, archive, destination=self.source_folder, strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        if os.name == "nt":
            toolchain.generator = "Ninja"
        if str(self.settings.os) == "OHOS":
            toolchain.variables["OHOS_ARCH"] = "arm64-v8a"
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["BUILD_STATIC_LIBS"] = (
            str(self.settings.os) == "OHOS" or not bool(self.options.shared)
        )
        toolchain.variables["INSTALL_STATIC_LIBS"] = not bool(self.options.shared)
        toolchain.variables["BUILD_gflags_LIB"] = True
        toolchain.variables["BUILD_gflags_nothreads_LIB"] = False
        toolchain.variables["BUILD_PACKAGING"] = False
        toolchain.variables["BUILD_TESTING"] = True
        toolchain.variables["INSTALL_HEADERS"] = True
        toolchain.variables["REGISTER_INSTALL_PREFIX"] = False
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build(cli_args=["--parallel", "2"])
        if cross_building(self):
            self.output.info("cross-building: upstream test binaries compiled but not executed")
        else:
            cmake.ctest(cli_args=["--output-on-failure", "-C", str(self.settings.build_type)])

    def package(self):
        CMake(self).install()
        rm(self, "gflags_completions.sh", os.path.join(self.package_folder, "bin"))
        self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        if not self.options.shared or str(self.settings.os) != "OHOS":
            return
        libraries = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True
        )
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            if cross_building(self):
                self.output.info("cross-building: target-only shared-library signing skipped")
                return
            self.output.warning(
                "OHOS binary-sign-tool is unavailable; preserving the linker-generated .codesign section"
            )
            return
        for library in libraries:
            if os.path.islink(library):
                continue
            # llvm-objcopy accepts a missing .codesign section; real errors must fail.
            self.run(
                '{} --remove-section .codesign "{}"'.format(objcopy, library)
            )
            self.run(
                '{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                    signer, library, library
                )
            )

    def package_info(self):
        self.cpp_info.libs = ["gflags"]
        self.cpp_info.set_property("cmake_file_name", "gflags")
        self.cpp_info.set_property("cmake_target_name", "gflags::gflags")
        self.cpp_info.set_property("pkg_config_name", "gflags")
