#!/usr/bin/env python3
"""Conan recipe — harminv 1.4.3 (HarmonyOS PC / os=OHOS arch=armv8)

harminv 谐波反演 C 库，依赖 BLAS/LAPACK。鸿蒙设备无 Fortran 编译器，
跳过 autotools 构建系统，直接编译源码并链接 LAPACK。

依赖:
  - lapack/3.12.1（提供 liblapack.a + libblas.a + FortranRuntime + FortranDecimal）
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import copy, apply_conandata_patches


class HarminvConan(ConanFile):
    name = "harminv"
    version = "1.4.3"
    description = "Harmonic inversion algorithm of Mandelshtam (C library + CLI tool)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/NanoComp/harminv"
    url = ""

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def requirements(self):
        self.requires("lapack/3.12.1")

    def export_sources(self):
        # No patches needed — direct compilation approach
        pass

    def source(self):
        # Download and extract
        from conan.tools.files import get
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        src = self.source_folder
        build = self.build_folder
        lapack_pkg = self.dependencies["lapack"].package_folder
        lapack_libdir = os.path.join(lapack_pkg, "lib")
        lapack_incdir = os.path.join(lapack_pkg, "include")

        # OHOS: Skip autotools entirely — compile directly.
        # The autotools build system on this platform fails because:
        #   1. No Fortran compiler (gfortran/flang) is available
        #   2. AX_BLAS/AX_LAPACK macros fail to find libraries in non-standard paths
        #   3. Stock config.guess doesn't recognize HarmonyOS
        # Direct compilation is more reliable and produces identical output.

        cc = "/data/service/hnp/bin/clang"
        cflags = [
            f'-DVERSION="{self.version}"',
            "-O2", "-DNDEBUG",
            f"-I{lapack_incdir}",
            "-DHAVE_CONFIG_H",
        ]

        # Debug: show what's in source folder
        self.output.info(f"src={src}")
        self.output.info(f"build={build}")
        self.output.info(f"src contents: {os.listdir(src)}")

        # Generate config.h
        with open(os.path.join(build, "config.h"), "w") as f:
            f.write(f'#define VERSION "{self.version}"\n')
            f.write(f'#define PACKAGE_VERSION "{self.version}"\n')
            f.write("#define F77_FUNC(name,NAME) name##_\n")
            f.write("#define F77_FUNC_(name,NAME) name##_\n")

        # Compile harminv.c
        self._run(f"{cc} {' '.join(cflags)} -c {src}/harminv.c -o {build}/harminv.o")
        self._run(f"{cc} {' '.join(cflags)} -c {src}/harminv-main.c -o {build}/harminv-main.o")

        # Create static lib
        self._run(f"ar rcs {build}/libharminv.a {build}/harminv.o")

        # Link binary
        ldflags = f"-L{lapack_libdir} -lblas -llapack -lFortranRuntime -lFortranDecimal -lm"
        self._run(f"{cc} {build}/harminv.o {build}/harminv-main.o {ldflags} -o {build}/harminv")

    def _run(self, cmd):
        self.output.info(f"RUN: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout:
            self.output.info(result.stdout)
        if result.returncode != 0:
            self.output.error(result.stderr)
            raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")

    def package(self):
        src = self.source_folder
        build = self.build_folder
        pkg = self.package_folder
        copy(self, "*.h", src=src, dst=os.path.join(pkg, "include"))
        copy(self, "*.a", src=build, dst=os.path.join(pkg, "lib"))
        copy(self, "harminv", src=build, dst=os.path.join(pkg, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "harminv")
        self.cpp_info.set_property("cmake_target_name", "harminv::harminv")
        self.cpp_info.libs = ["harminv"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["m"]
