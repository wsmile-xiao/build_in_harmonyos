#!/usr/bin/env python3
"""Conan recipe for qpOASES 3.2.1 (C++ QP solver, upstream release 3.2.1).

qpOASES is an implementation of the online active set strategy for solving
parametric quadratic programming (QP) problems.  It is a **self-contained** C++
library: it ships its own BLAS/LAPACK replacement (``src/BLASReplacement.cpp``
and ``src/LAPACKReplacement.cpp``) and therefore has **no external
dependencies**, which makes it a clean cross-compile target.

Upstream offers two build entry points:

* ``CMakeLists.txt`` -- builds the ``qpOASES`` static library plus the example
  programs (``example1`` .. ``exampleLP``, ``qrecipe``, ``qrecipeSchur``).
  Note upstream hardcodes ``ADD_LIBRARY(qpOASES STATIC ...)``, so ``shared``
  is not honoured; the package is always static.
* ``make.mk`` + ``testing/cpp/Makefile`` -- builds the 30-source upstream unit
  test suite that ``testing/runUnitTests`` drives.

The recipe drives CMake for the library and additionally builds the upstream
unit test suite, so the OHOS package is validated by the real upstream tests
rather than by a hand-written stub.

Upstream test exit-code semantics (see ``testing/runUnitTests``): ``0`` = pass,
``99`` = the test's external problem data is unavailable, anything else = a
genuine failure.  The data set lived on a now-retired COIN-OR SVN server
(``testing/cpp/data/fetch_cpp_data``), so only tests that are self-contained
can report a real verdict; that split is recorded in ``test_package/MANIFEST.yml``.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

required_conan_version = ">=2.0"


class QpoasesConan(ConanFile):
    name = "qpoases"
    version = "3.2.1"
    package_type = "library"
    description = ("qpOASES - an implementation of the online active set strategy for "
                   "parametric quadratic programming (self-contained C++ QP solver)")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/coin-or/qpOASES"
    url = ("https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/"
           "tree/main/archives/q/qpoases/3.2.1")
    topics = ("quadratic-programming", "optimization", "active-set", "numerical")

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        # Build and execute the upstream unit test suite (testing/cpp).
        "run_upstream_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "run_upstream_tests": True,
    }

    def export_sources(self):
        export_conandata_patches(self)
        # The upstream test driver is needed inside build() to execute the
        # cross-built upstream test binaries.
        copy(self, "run-ohos-tests.py", src=self.recipe_folder,
             dst=os.path.join(self.export_sources_folder))

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name}/{self.version} is only validated for Linux/OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["QPOASES_BUILD_EXAMPLES"] = True
        tc.cache_variables["CMAKE_BUILD_TYPE"] = str(self.settings.build_type)
        # Upstream declares `cmake_minimum_required(VERSION 2.6)`. CMake >= 4
        # removed compatibility with < 3.5 and aborts during configure with
        #   Compatibility with CMake < 3.5 has been removed from CMake.
        #   Or, add -DCMAKE_POLICY_VERSION_MINIMUM=3.5 to try configuring anyway.
        # The CI worker ships a newer CMake than the local toolchain, so set the
        # policy floor explicitly instead of patching upstream's CMakeLists.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if self.settings.os == "OHOS":
            # E092: CMake ships no Platform/HarmonyOS module. The OHOS toolchain
            # already targets aarch64-linux-ohos, so pin the generic Linux
            # platform module for the configure step.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.user_presets_path = False
        tc.generate()

    # ------------------------------------------------------------------ tests
    def _cross_cxx(self):
        """Return (compiler, extra flags) for the OHOS target."""
        conf = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = conf.get("cpp") or os.environ.get("CXX") or "c++"
        flags = []
        sysroot = self.conf.get("tools.build:sysroot")
        if sysroot:
            flags.append("--sysroot=%s" % sysroot)
        if self.settings.os == "OHOS":
            flags.append("--target=aarch64-linux-ohos")
        return cxx, flags

    def _build_upstream_tests(self, build_dir):
        """Compile the upstream unit test suite (testing/cpp/*.cpp).

        ``testing/cpp/Makefile`` inherits from ``make.mk``, which hardcodes a
        native ``g++`` and native flags, so it cannot be reused for cross
        compilation.  The 30 sources are self-contained translation units that
        only need the public headers plus ``libqpOASES.a``, so they are
        compiled here with an explicit cross-compiler invocation.
        """
        tests_dir = os.path.join(self.source_folder, "testing", "cpp")
        out_dir = os.path.join(build_dir, "upstream-tests")
        os.makedirs(out_dir, exist_ok=True)

        libs = glob.glob(os.path.join(build_dir, "**", "libqpOASES.a"), recursive=True)
        if not libs:
            raise ConanException(f"libqpOASES.a not found under {build_dir}")
        lib = libs[0]

        cxx, xflags = self._cross_cxx()
        cxxflags = ["-std=c++11", "-O2", "-w", "-D__NO_COPYRIGHT__"] + xflags
        include_args = ['-I"%s"' % tests_dir,
                        '-I"%s"' % os.path.join(self.source_folder, "include")]

        built = 0
        for src in sorted(glob.glob(os.path.join(tests_dir, "test_*.cpp"))):
            exe = os.path.join(out_dir, os.path.basename(src)[:-4])
            cmd = '"%s" %s %s "%s" "%s" -lm -o "%s"' % (
                cxx, " ".join(cxxflags), " ".join(include_args), src, lib, exe)
            self.run(cmd)
            built += 1
        self.output.info("built %d upstream test binaries" % built)
        return out_dir

    def _emulator(self):
        """Return the cross-compilation emulator command, if the profile sets one.

        The OHOS ``*-run`` profile injects ``CMAKE_CROSSCOMPILING_EMULATOR``
        (a qemu-aarch64 wrapper with the OHOS musl run root), which is exactly
        what is needed to execute the cross-built test binaries locally.
        """
        extra = self.conf.get("tools.cmake.cmaketoolchain:extra_variables",
                              default={}, check_type=dict)
        emu = extra.get("CMAKE_CROSSCOMPILING_EMULATOR")
        if isinstance(emu, (list, tuple)):
            return [str(e) for e in emu]
        if emu:
            return [str(emu)]
        return []

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if self.options.run_upstream_tests:
            tests_dir = self._build_upstream_tests(self.build_folder)
            emu = self._emulator()
            if can_run(self) or emu:
                # Run the upstream suite. When cross-compiling, prepend the
                # profile's emulator so the aarch64 binaries actually execute.
                cmd = 'python3 -u "%s" "%s"' % (
                    os.path.join(self.source_folder, "run-ohos-tests.py"), tests_dir)
                if emu:
                    cmd += " --emulator %s" % " ".join('"%s"' % e for e in emu)
                self.run(cmd, cwd=self.build_folder)
            else:
                self.output.warning(
                    "no emulator configured and cannot run natively: "
                    "upstream tests were built but not executed")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Upstream installs a bare .a and headers only; drop any stray cmake dir.
        import shutil
        stray = os.path.join(self.package_folder, "lib", "cmake")
        if os.path.isdir(stray):
            shutil.rmtree(stray)

    def package_info(self):
        # Upstream CMakeLists hardcodes a STATIC library and installs it to lib/.
        self.cpp_info.libs = ["qpOASES"]
        self.cpp_info.set_property("cmake_file_name", "qpOASES")
        self.cpp_info.set_property("cmake_target_name", "qpOASES::qpOASES")
