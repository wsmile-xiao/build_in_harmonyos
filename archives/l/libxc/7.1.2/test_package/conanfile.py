#!/usr/bin/env python3
"""Conan consumer tests for libxc 7.1.2 C and Fortran KXC targets."""

import glob
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv


class LibxcTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0", package_id_mode="full_mode")

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "libxc test_package must run on os=OHOS, arch=armv8"
            )

    def layout(self):
        cmake_layout(self)

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
                "libxc tests require exactly one complete OHOS SDK; set "
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
        CMakeDeps(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        flang, fortran_flags, runtime_dirs = self._fortran_toolchain()
        build_env = Environment()
        build_env.define_path("LD_LIBRARY_PATH", list(runtime_dirs))
        build_env.vars(self).save_script("libxc_fortran_build_env")
        toolchain = CMakeToolchain(self)
        toolchain.variables["CMAKE_Fortran_COMPILER"] = flang
        toolchain.variables["CMAKE_Fortran_FLAGS"] = fortran_flags
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        for executable in ("test_libxc_c", "test_libxc_fortran_kxc"):
            path = os.path.join(self.cpp.build.bindirs[0], executable)
            self.run('"{}"'.format(path), env="conanrun", cwd=self.build_folder)
