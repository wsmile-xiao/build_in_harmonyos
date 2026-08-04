#!/usr/bin/env python3
"""Conan recipe for libxc 7.1.2 with C and Fortran KXC interfaces."""

import glob
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
    rm,
)


class LibxcConan(ConanFile):
    name = "libxc"
    version = "7.1.2"
    description = "Exchange-correlation functionals for density-functional theory"
    license = "MPL-2.0"
    homepage = "https://libxc.gitlab.io/"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "*.cmake",
            src=os.path.join(self.recipe_folder, "cmake"),
            dst=os.path.join(self.export_sources_folder, "cmake"),
        )

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "libxc/7.1.2 is validated only for os=OHOS, arch=armv8"
            )

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0", package_id_mode="full_mode")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _sdk_native(self):
        configured = self.conf.get(
            "user.libxc:sdk_native", default=None, check_type=str
        )
        candidates = (
            [configured]
            if configured
            else glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native")
        )
        valid = []
        for candidate in candidates:
            candidate = os.path.realpath(candidate)
            required_dirs = (
                os.path.join(candidate, "sysroot"),
                os.path.join(candidate, "llvm", "bin"),
                os.path.join(candidate, "llvm", "lib"),
                os.path.join(candidate, "llvm", "lib", "aarch64-linux-ohos"),
            )
            clang = os.path.join(candidate, "llvm", "bin", "clang")
            if (
                all(os.path.isdir(path) for path in required_dirs)
                and os.path.isfile(clang)
                and os.access(clang, os.X_OK)
            ):
                valid.append(candidate)
        valid = sorted(set(valid))
        if len(valid) != 1:
            raise ConanInvalidConfiguration(
                "libxc requires exactly one complete OHOS SDK; set "
                "user.libxc:sdk_native when automatic discovery is ambiguous"
            )
        return valid[0]

    def _fortran_toolchain(self):
        flang_package = self.dependencies.build["flang-ohos"].package_folder
        flang = os.path.join(flang_package, "bin", "flang")
        flang_lib = os.path.join(flang_package, "lib")
        if not os.path.isfile(flang) or not os.path.isdir(flang_lib):
            raise ConanInvalidConfiguration("flang-ohos tool package is incomplete")
        sdk_native = self._sdk_native()
        sdk_clang = os.path.join(sdk_native, "llvm", "bin", "clang")
        runtime_dirs = (
            os.path.join(sdk_native, "llvm", "lib"),
            flang_lib,
        )
        probe_env = os.environ.copy()
        probe_env["LD_LIBRARY_PATH"] = os.pathsep.join(runtime_dirs)
        try:
            resource_dir = subprocess.run(
                [sdk_clang, "-print-resource-dir"],
                check=True,
                env=probe_env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError) as error:
            raise ConanInvalidConfiguration(
                "failed to query the selected OHOS SDK Clang resource directory"
            ) from error
        resource_dir = os.path.realpath(resource_dir)
        if (
            not os.path.isdir(resource_dir)
            or os.path.commonpath((sdk_native, resource_dir)) != sdk_native
        ):
            raise ConanInvalidConfiguration(
                "selected OHOS SDK Clang returned an external resource directory"
            )
        flags = [
            "--target=aarch64-unknown-linux-ohos",
            "--sysroot={}".format(os.path.join(sdk_native, "sysroot")),
            "-resource-dir={}".format(resource_dir),
            "-B{}".format(os.path.join(sdk_native, "llvm", "bin")),
            "-L{}".format(
                os.path.join(sdk_native, "llvm", "lib", "aarch64-linux-ohos")
            ),
        ]
        return (
            flang.replace("\\", "/"),
            " ".join(flags).replace("\\", "/"),
            runtime_dirs,
        )

    def generate(self):
        VirtualBuildEnv(self).generate()
        flang, fortran_flags, runtime_dirs = self._fortran_toolchain()
        build_env = Environment()
        build_env.define_path("LD_LIBRARY_PATH", list(runtime_dirs))
        build_env.vars(self).save_script("libxc_fortran_build_env")
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = False
        toolchain.variables["BUILD_TESTING"] = False
        toolchain.variables["ENABLE_FORTRAN"] = True
        toolchain.variables["ENABLE_PYTHON"] = False
        toolchain.variables["MAXORDER"] = "3"
        toolchain.variables["FORTRAN_MODULE_INSTALL_DIR"] = "include"
        toolchain.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        toolchain.variables["CMAKE_INSTALL_INCLUDEDIR"] = "include"
        toolchain.variables["CMAKE_Fortran_COMPILER"] = flang
        toolchain.variables["CMAKE_Fortran_FLAGS"] = fortran_flags
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "libxc-fortran-abi.cmake",
            src=os.path.join(self.export_sources_folder, "cmake"),
            dst=os.path.join(self.package_folder, "lib", "cmake", "Libxc"),
        )
        bindir = os.path.join(self.package_folder, "bin")
        rm(self, "xc-info", bindir)
        rmdir(self, bindir)

        required = (
            os.path.join("lib", "libxc.a"),
            os.path.join("lib", "libxcf03.a"),
            os.path.join("include", "xc_f03_lib_m.mod"),
            os.path.join("include", "xc_f03_funcs_m.mod"),
        )
        missing = [
            relative
            for relative in required
            if not os.path.isfile(os.path.join(self.package_folder, relative))
        ]
        if missing:
            raise ConanException(
                "libxc package is missing required artifacts: {}".format(
                    ", ".join(missing)
                )
            )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Libxc")
        self.cpp_info.set_property(
            "cmake_build_modules",
            ["lib/cmake/Libxc/libxc-fortran-abi.cmake"],
        )

        xc = self.cpp_info.components["xc"]
        xc.libs = ["xc"]
        xc.system_libs = ["m"]
        xc.set_property("cmake_target_name", "Libxc::xc")
        xc.set_property("pkg_config_name", "libxc")

        xcf03 = self.cpp_info.components["xcf03"]
        xcf03.libs = ["xcf03"]
        xcf03.requires = ["xc"]
        xcf03.set_property("cmake_target_name", "Libxc::xcf03")
        xcf03.set_property("pkg_config_name", "libxcf03")
