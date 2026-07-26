#!/usr/bin/env python3
"""Conan recipe — PETSc 3.25.3 (Python configure)."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PetscConan(ConanFile):
    name = "petsc"
    version = "3.25.3"
    description = "Portable, Extensible Toolkit for Scientific Computation"
    license = "BSD-2-Clause"
    homepage = "https://petsc.org/"
    url = "https://gitlab.com/petsc/petsc"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"
        ar = compilers.get("ar") or "llvm-ar"
        ranlib = compilers.get("ranlib") or "llvm-ranlib"
        shared = "1" if self.options.shared else "0"
        arch = "arch-ohos-c-opt" if str(self.settings.os) == "OHOS" else "arch-conan-c-opt"
        is_debug = str(self.settings.build_type) == "Debug"
        debugging = "1" if is_debug else "0"
        optflags = "-fPIC -g -O0" if is_debug else "-fPIC -O2"

        configure_args = [
            f"--prefix={self.package_folder}",
            f"--with-cc={cc}",
            f"--with-cxx={cxx}",
            "--with-fc=0",
            "--with-mpi=0",
            f"--with-shared-libraries={shared}",
            f"--with-debugging={debugging}",
            "--download-f2cblaslapack=1",
            f"COPTFLAGS='{optflags}'",
            f"CXXOPTFLAGS='{optflags}'",
            f"AR={ar}",
            f"RANLIB={ranlib}",
        ]
        self.run(f"python3 ./configure {' '.join(configure_args)}", cwd=self.source_folder)
        self.run(f"make PETSC_DIR={self.source_folder} PETSC_ARCH={arch} all", cwd=self.source_folder)

    def package(self):
        arch = "arch-ohos-c-opt" if str(self.settings.os) == "OHOS" else "arch-conan-c-opt"
        self.run(f"make PETSC_DIR={self.source_folder} PETSC_ARCH={arch} install", cwd=self.source_folder)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["petsc", "f2clapack", "f2cblas"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "petsc")]
        self.cpp_info.defines = ["PETSC_USE_REAL_DOUBLE"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "stdc++"]
