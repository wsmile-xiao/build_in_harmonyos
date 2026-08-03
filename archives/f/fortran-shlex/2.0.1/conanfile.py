#!/usr/bin/env python3
"""Conan recipe for fortran-shlex 2.0.1 on HarmonyOS PC.

The upstream fpm project contains one Fortran module and one test program.
The recipe performs the equivalent compilation directly with the published
flang-ohos tool package, so fpm is not required at package build time.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class FortranShlexConan(ConanFile):
    name = "fortran-shlex"
    version = "2.0.1"
    description = "Modern Fortran shell-like lexer with POSIX and Windows command-line support"
    license = "MIT"
    homepage = "https://github.com/perazz/fortran-shlex"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "fortran-shlex is built natively on HarmonyOS PC "
                "(os=OHOS, arch=armv8)"
            )

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(
            self,
            **self.conan_data["sources"][self.version],
            strip_root=True,
        )

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _tools(self):
        flang_package = self.dependencies.build["flang-ohos"].package_folder
        flang = os.path.join(flang_package, "bin", "flang")
        fortran_runtime = os.path.join(
            flang_package, "lib", "libFortranRuntime.a"
        )
        fortran_decimal = os.path.join(
            flang_package, "lib", "libFortranDecimal.a"
        )

        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        clang = compilers.get("c", "/data/service/hnp/bin/clang")
        llvm_ar = os.path.join(os.path.dirname(clang), "llvm-ar")
        if not os.path.isfile(llvm_ar):
            # GNU ar and llvm-ar both create architecture-neutral Unix static
            # archives; this fallback also supports device images whose HNP
            # tool directory exposes only the compiler driver.
            llvm_ar = shutil.which("llvm-ar") or shutil.which("ar") or llvm_ar

        for tool in (
            flang,
            clang,
            llvm_ar,
            fortran_runtime,
            fortran_decimal,
        ):
            if not os.path.isfile(tool):
                raise ConanInvalidConfiguration(
                    "required native HarmonyOS build tool is missing: {}".format(tool)
                )
        return flang, clang, llvm_ar, fortran_runtime, fortran_decimal

    def build(self):
        apply_conandata_patches(self)
        (
            flang,
            clang,
            llvm_ar,
            fortran_runtime,
            fortran_decimal,
        ) = self._tools()

        module_dir = os.path.join(self.build_folder, "modules")
        library_dir = os.path.join(self.build_folder, "lib")
        os.makedirs(module_dir, exist_ok=True)
        os.makedirs(library_dir, exist_ok=True)

        source = os.path.join(self.source_folder, "src", "shlex_module.f90")
        object_file = os.path.join(self.build_folder, "shlex_module.o")
        library = os.path.join(library_dir, "libfortran-shlex.a")

        self.run(
            '"{fc}" -O2 -fPIC -J"{mods}" -I"{mods}" '
            '-c "{src}" -o "{obj}"'.format(
                fc=flang,
                mods=module_dir,
                src=source,
                obj=object_file,
            ),
            env="conanbuild",
        )
        self.run(
            '"{ar}" rcs "{lib}" "{obj}"'.format(
                ar=llvm_ar,
                lib=library,
                obj=object_file,
            )
        )

        # Upstream's official fpm test target compiles this single program.
        # Linking it against the just-built archive exercises the exact same
        # 363 POSIX, MSVCRT, UCRT and quoting checks.
        upstream_test_source = os.path.join(
            self.source_folder,
            "test",
            "shlex_test.f90",
        )
        upstream_test_binary = os.path.join(
            self.build_folder,
            "fortran_shlex_upstream_tests",
        )
        upstream_test_object = os.path.join(
            self.build_folder,
            "shlex_test.o",
        )
        self.run(
            '"{fc}" -O2 -I"{mods}" "{test_src}" '
            '-c -o "{test_obj}"'.format(
                fc=flang,
                mods=module_dir,
                test_src=upstream_test_source,
                test_obj=upstream_test_object,
            ),
            env="conanbuild",
        )
        # flang-ohos packages the Fortran frontend and runtime, but not an
        # OHOS SDK sysroot or Clang resource directory.  Use the profile's
        # native OHOS Clang driver for the final link so it supplies the
        # platform CRT, libc, libunwind and compiler-rt objects.
        self.run(
            '"{cc}" "{test_obj}" -L"{libdir}" -lfortran-shlex '
            '"{runtime}" "{decimal}" -lm -o "{test_bin}"'.format(
                cc=clang,
                test_obj=upstream_test_object,
                libdir=library_dir,
                runtime=fortran_runtime,
                decimal=fortran_decimal,
                test_bin=upstream_test_binary,
            )
        )
        self.run('"{test_bin}"'.format(test_bin=upstream_test_binary),
                 env="conanbuild")

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "libfortran-shlex.a",
            src=os.path.join(self.build_folder, "lib"),
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "shlex_module.mod",
            src=os.path.join(self.build_folder, "modules"),
            dst=os.path.join(self.package_folder, "include"),
        )

    def package_info(self):
        self.cpp_info.libs = ["fortran-shlex"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
