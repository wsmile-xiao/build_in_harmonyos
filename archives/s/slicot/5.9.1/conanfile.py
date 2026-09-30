#!/usr/bin/env python3
"""Conan recipe for SLICOT 5.9.1 — Subroutine Library In COntrol Theory.

HarmonyOS (aarch64) adaptation.  SLICOT is a large Fortran 77 numerical
library (control/ systems theory: ~1500 routines).  Upstream ships a CMake
project (C + Fortran) that hard-requires BLAS and LAPACK via
``find_package(BLAS/LAPACK REQUIRED)`` and, when built as the top-level
project, also builds the ``examples/`` programs and registers one CTest per
example (242 of them, each comparing against a reference ``.res`` file).

Toolchain: the device has no gfortran; the repository's ``flang-ohos/20.1.0``
LLVM Flang toolchain is used via ``tool_requires`` (same as blas / lapack /
arpack-ng).  Because the flang runtime set cannot complete CMake's Fortran
link probes, the usual OHOS settings are applied (CMAKE_SYSTEM_NAME=Linux,
STATIC_LIBRARY try-compiles, forced C/C++ compilers), following the
arpack-ng 3.9.1 precedent.

R32: settings.os must check in ("Linux", "OHOS").
R51: the upstream CTest suite (examples) is built and really executed.
R38: a library package ships no bin/ executables -> no commands.json.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class SlicotConan(ConanFile):
    name = "slicot"
    version = "5.9.1"
    description = ("SLICOT — Subroutine Library In COntrol Theory: numerical "
                   "routines for systems and control theory (Fortran 77)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/SLICOT/SLICOT-Reference"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"slicot is supported only on Linux/OHOS, got {self.settings.os}")

    def requirements(self):
        # SLICOT links the reference BLAS and LAPACK.
        self.requires("blas/3.12.1")
        self.requires("lapack/3.12.1")

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _sdk_llvm(self):
        g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm"))
        if not g:
            raise ConanException("ohos-sdk llvm toolchain directory not found")
        return g[-1]

    def _flang(self):
        return os.path.join(
            self.dependencies.build["flang-ohos"].package_folder, "bin", "flang")

    def _fortran_runtime(self):
        return os.path.join(
            self.dependencies.build["flang-ohos"].package_folder, "lib")

    def generate(self):
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        fc = self._flang()
        sdk = self._sdk_llvm()
        rt_lib = os.path.join(flang_pkg, "lib")

        # flang / lld need the SDK llvm libs and the flang package libs at run
        # time; clear HiShell-polluted build vars (blas / arpack-ng precedent).
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            [os.path.join(sdk, "lib"), rt_lib]
            + [p for p in [os.environ.get("LD_LIBRARY_PATH", "")] if p])
        for k in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "FFLAGS"):
            os.environ.pop(k, None)
        # OHOS: make jobserver FIFO creation fails -> single job.
        os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"

        # BLAS/LAPACK from the Conan packages (upstream find_package(BLAS/LAPACK
        # REQUIRED)); give CMake the concrete archives and vendor so it does not
        # probe the environment.
        blas = self.dependencies["blas"]
        lapack = self.dependencies["lapack"]
        blas_libs = ";".join(
            os.path.join(blas.package_folder, "lib", "lib%s.a" % n)
            for n in ("blas",))
        # lapack's package declares lapack+blas+FortranRuntime+FortranDecimal
        lapack_libs = ";".join(
            os.path.join(lapack.package_folder, "lib", "lib%s.a" % n)
            for n in ("lapack",))
        link_extra = ";".join(
            [os.path.join(rt_lib, "libFortranRuntime.a"),
             os.path.join(rt_lib, "libFortranDecimal.a"),
             os.path.join(sdk, "lib", "aarch64-linux-ohos", "libm.so")])

        tc = CMakeToolchain(self)
        tc.user_presets_path = False
        tc.variables["CMAKE_Fortran_COMPILER"] = fc
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # Build the upstream example programs and their CTest registrations.
        tc.variables["SLICOT_TESTING"] = True
        # Upstream src/CMakeLists.txt probes LAPACK for the removed legacy
        # routines (dgegv/zgegv/dlatzm/zlatzm/dgegs/zgegs) with
        # Check_Fortran_Function_Exists and only then compiles its own
        # copies from src/lapack_aux/.  On OHOS the probe cannot link (the
        # toolchain forces CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY), so
        # it wrongly reports the symbols as present and the legacy routines
        # are never built -> the examples link with "undefined symbol:
        # dgegv_".  LAPACK 3.12 has genuinely removed them, so pin the probe
        # results to FALSE and let upstream compile its own implementations.
        for var in ("HAVE_DGEGS", "HAVE_ZGEGS", "HAVE_DLAZTM", "HAVE_ZLAZTM",
                    "HAVE_DGEGV", "HAVE_ZGEGV"):
            tc.cache_variables[var] = False
        # Feed BLAS/LAPACK directly.
        tc.variables["BLAS_LIBRARIES"] = blas_libs
        tc.variables["LAPACK_LIBRARIES"] = lapack_libs
        tc.variables["BLA_VENDOR"] = "Generic"
        tc.variables["CMAKE_REQUIRED_LIBRARIES"] = link_extra
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
            tc.variables["CMAKE_C_COMPILER_FORCED"] = True
            tc.variables["CMAKE_CXX_COMPILER_FORCED"] = True
            sysroot = os.path.join(sdk, "..", "sysroot")
            tc.extra_cflags.append("--sysroot=%s" % sysroot)
            tc.extra_cxxflags.append("--sysroot=%s" % sysroot)
            # flang resolves its own runtime objects (crtbeginS.o / crtendS.o,
            # libclang_rt.builtins.a, libunwind.a) through -resource-dir.  The
            # flang-ohos package does NOT ship lib/clang/...: its package()
            # copies only bin/ plus the Fortran runtime .a/.so.  Without an
            # explicit resource dir the driver looks under
            # <flang pkg>/lib/clang/20, so every example executable fails to
            # link with
            #   ld.lld: cannot open crtbeginS.o
            #   ld.lld: cannot open .../lib/clang/20/lib/.../libclang_rt.builtins.a
            #   ld.lld: unable to find library -l:libunwind.a
            # Point it at the SDK's clang resource tree, which does carry the
            # aarch64-linux-ohos crt objects, builtins and libunwind.a
            # (blas/3.12.1 passes the same resource dir on its FC line).
            res_dir = sorted(glob.glob(os.path.join(sdk, "lib", "clang", "*")))[-1]
            link_flags = ["--sysroot=%s" % sysroot,
                          "-resource-dir=%s" % res_dir,
                          "-L%s" % os.path.join(sdk, "lib", "aarch64-linux-ohos"),
                          "-L%s" % rt_lib,
                          os.path.join(rt_lib, "libFortranRuntime.a"),
                          os.path.join(rt_lib, "libFortranDecimal.a"),
                          "-lm"]
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = " ".join(link_flags)
            tc.variables["CMAKE_Fortran_LINK_FLAGS"] = " ".join(link_flags)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.settings.os == "OHOS":
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream CTest suite (one test per examples/*.f)."""
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        sdk = self._sdk_llvm()
        env_ld = os.pathsep.join([
            os.path.join(sdk, "lib", "aarch64-linux-ohos"),
            os.path.join(flang_pkg, "lib"),
            os.path.join(self.dependencies["lapack"].package_folder, "lib"),
            os.path.join(self.dependencies["blas"].package_folder, "lib"),
            "/system/lib64",
            os.environ.get("LD_LIBRARY_PATH", ""),
        ])
        env = Environment()
        env.define("LD_LIBRARY_PATH", env_ld)
        env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        with env.vars(self).apply():
            self.run('ctest --test-dir "%s" --output-on-failure' % self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SLICOT")
        self.cpp_info.set_property("cmake_target_name", "SLICOT::slicot")
        self.cpp_info.libs = ["slicot"]
        # SLICOT's public headers (Fortran-callable, plus the f2c-style
        # slicot.h helper) live under the install include dir.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = ["blas::blas", "lapack::lapack"]
        self.cpp_info.system_libs = ["m"]
