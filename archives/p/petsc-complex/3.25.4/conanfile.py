#!/usr/bin/env python3
"""Conan recipe — PETSc 3.25.4, complex-scalar variant (`petsc-complex`).

Same upstream source as `petsc/3.25.4`, but configured with
`--with-scalar-type=complex`.  That knob is *not* an option of `petsc`: it
changes the ABI (`PetscScalar` becomes C99 `double _Complex`, i.e.
`2 * sizeof(PetscReal`) and rewrites `petscconf.h`, so it must live in its own
Conan package — otherwise two consumers needing different scalar types could
never be resolved in the same graph.

BLAS/LAPACK are taken from PETSc's bundled `f2cblaslapack` (`zgemm`, `zdotc`,
`zheev` are f2c'd from netlib), so the complex variant stays self-contained:
no OpenBLAS/MKL is required and no external provider is needed for a complex
build.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PetscComplexConan(ConanFile):
    name = "petsc-complex"
    version = "3.25.4"
    description = "PETSc complex-scalar build — Portable, Extensible Toolkit for Scientific Computation"
    license = "BSD-2-Clause"
    homepage = "https://petsc.org/"
    url = "https://gitlab.com/petsc/petsc"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

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
        arch = self._arch()
        is_debug = str(self.settings.build_type) == "Debug"
        debugging = "1" if is_debug else "0"
        optflags = "-fPIC -g -O0" if is_debug else "-fPIC -O2"

        configure_args = [
            f"--prefix={self.package_folder}",
            f"--with-cc={cc}",
            f"--with-cxx={cxx}",
            "--with-fc=0",
            "--with-mpi=0",
            # PETSc names its build tree arch-<sys.platform>-<clang>-<opt>; on the
            # Linux build host that is arch-linux-c-opt, so the name handed to
            # make/install has to be told to configure as well or the two
            # disagree and make looks into a directory that was never created.
            f"--with-petsc-arch={arch}",
            # OHOS has no X11; without this, configure auto-detects the *build
            # host's* libX11 headers and links the X draw backends into
            # libpetsc.a, which then forces -lX11 on every consumer.
            "--with-x=0",
            # the whole point of this package: complex scalars, double precision
            "--with-scalar-type=complex",
            "--with-precision=double",
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
        arch = self._arch()
        self.run(f"make PETSC_DIR={self.source_folder} PETSC_ARCH={arch} install", cwd=self.source_folder)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["petsc", "f2clapack", "f2cblas"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "petsc")]
        # PETSC_USE_COMPLEX is also baked into the installed petscconf.h; repeating
        # it here keeps the ABI macro visible to consumers that never see that
        # header (e.g. -D-only consumers) and makes the variant explicit in the
        # generated CMake/pkg-config files.
        self.cpp_info.defines = ["PETSC_USE_REAL_DOUBLE", "PETSC_USE_COMPLEX"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "stdc++"]
        self.cpp_info.set_property("cmake_file_name", "petsc-complex")
        self.cpp_info.set_property("cmake_target_name", "petsc-complex::petsc-complex")
        self.cpp_info.set_property("pkg_config_name", "petsc-complex")

    def _arch(self):
        return "arch-ohos-c-opt" if str(self.settings.os) == "OHOS" else "arch-conan-c-opt"
