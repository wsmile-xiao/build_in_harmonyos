#!/usr/bin/env python3
"""Conan recipe — libvcflib 1.0.12 for OpenHarmony.

Upstream project name is ``vcflib`` (https://github.com/vcflib/vcflib); the packaged
artifact is its C++ library ``libvcflib.a`` plus the command line tools the upstream
install rules produce.

Build system
------------
CMake is the authoritative entry point.  The top level ``Makefile`` is a thin wrapper
(``all: cd build && cmake -DCMAKE_INSTALL_PREFIX=$(VCF_LIB_LOCAL) .. && make && make
install``), and its ``make test`` target is stale: it calls ``prove -Itests/lib
tests/*.t`` while this release ships its tests under ``test/`` (pytest + doctest files
registered with CTest).  The upstream CI therefore configures with CMake and runs
``cd build && ctest --verbose`` (``.github/workflows/ci_test.yml``).

Source archive
--------------
The release asset ``vcflib-1.0.12-src.tar.gz`` is the only self-contained tarball.
GitHub's ``/archive/refs/tags/v1.0.12.tar.gz`` ships **empty** ``contrib/*`` submodule
directories (tabixpp, fastahack, smithwaterman, filevercmp, fsom, intervaltree,
multichoose, WFA2-lib) and an empty ``src/simde``, so CMake fails at configure time with
``Cannot find source file: contrib/fastahack/Fasta.cpp``.  Googletest is listed in
``.gitmodules`` but is not referenced by CMakeLists.txt and is not needed.

Vendored dependency boundary (why nothing is fetched at build time)
------------------------------------------------------------------
Everything the build compiles is inside the ``-src`` asset: tabixpp is compiled from
``contrib/tabixpp/tabix.cpp`` into ``libvcflib.a`` (``pkg_check_modules(TABIXPP ...)``
finds no system tabixpp, so upstream falls back to the vendored copy), WFA2 comes from
``contrib/WFA2-lib`` via ``-DWFA_GITMODULE=ON`` (there is no OHOS package for libwfa2),
fastahack/smithwaterman/filevercmp/fsom/c-progress-bar/intervaltree are compiled from
``contrib/``.  Only two of the upstream dependencies are taken from the OHOS registry:
htslib (headers of ``src/Variant.h`` -> ``<tabix.hpp>`` -> ``htslib/*.h``) and bzip2.

Toolchain switches (all forced, none is a test-only switch)
-----------------------------------------------------------
* ``ZIG=OFF`` — the zig sub-project (``src/zig``) is only used by ``vcfcreatemulti``'s
  newer code paths.  zig is not part of the OHOS toolchain, and the registry build.zig
  API of zig 0.15/0.16 rejects this project's 0.13 era ``build.zig``.
* ``WFA_GITMODULE=ON`` — build the vendored WFA2 instead of ``find_library(wfa2)``.
* ``OPENMP=OFF`` — upstream's ``if(OPENMP)`` block only injects ``${OpenMP_C_FLAGS}``
  (the project never calls ``find_package(OpenMP)``, the variable is populated by
  ``include(FindOpenMP)``); on the OHOS build host that resolves to homebrew's libomp
  and emits ``-fopenmp=libomp``, which the OHOS clang does not provide.  With ``OFF``
  no OpenMP flag is injected and the ``#pragma omp`` directives are ignored, exactly
  like a build on a machine without libomp.
* ``BUILD_SHARED_LIBS=OFF`` — upstream builds ``add_library(vcflib STATIC ...)``; the
  recipe only supports static builds (see ``configure()``).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    mkdir,
    rm,
)
from conan.tools.gnu import PkgConfigDeps

# CTest tests whose harness cannot run on OHOS (see build()); reported as NOT_RUN.
CTEST_EXCLUDE = "vcfallelicprimitives|wfa2lib"


class LibvcflibConan(ConanFile):
    name = "libvcflib"
    version = "1.0.12"
    description = (
        "C++ library for parsing and manipulating VCF files, with the upstream "
        "command line tools"
    )
    license = "MIT"
    homepage = "https://github.com/vcflib/vcflib"
    url = "https://github.com/vcflib/vcflib"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "vcflib 1.0.12 only produces a static archive "
                "(add_library(vcflib STATIC ...) in CMakeLists.txt); shared builds are "
                "not supported by this recipe"
            )

    def requirements(self):
        # Direct dependencies of the upstream build.  htslib also brings xz,
        # libdeflate and its own zlib requirement; zlib is named explicitly because
        # CMakeLists.txt calls find_package(ZLIB) with TYPE REQUIRED and links
        # ${ZLIB_LIBRARIES}, bzip2 because include(FindBZip2) feeds
        # ${BZIP2_LIBRARIES} straight into the link line.
        #
        # transitive_headers=True is required for htslib: the public header
        # src/Variant.h includes <tabix.hpp>, which includes <htslib/*.h>.  Conan 2
        # defaults transitive_headers to False, and then a consumer of this package
        # gets only our own include dir and fails with
        # "'htslib/bgzf.h' file not found" while compiling Variant.h (measured on the
        # conan-generated CMakeDeps metadata: the transitive htslib data file carried
        # an empty INCLUDE_DIRS).  Traceback of the fix:
        # `requires("htslib/1.24-r0", transitive_headers=True)` restores
        # `htslib_INCLUDE_DIRS_RELEASE = <pkg>/include` in the consumer graph.
        # zlib/bzip2 are linked but not included by our public headers, so plain
        # transitive_libs (the default) is enough for them.
        self.requires("htslib/1.24-r0", transitive_headers=True)
        self.requires("zlib/1.3.1")
        self.requires("bzip2/1.0.8")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # pkg-config files for CMake's pkg_check_modules(htslib) inside the project.
        PkgConfigDeps(self).generate()
        # CMake config files so find_package(ZLIB)/find_package(CURL) resolve to the
        # Conan packages instead of whatever happens to be installed on the build host.
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["ZIG"] = "OFF"
        tc.variables["WFA_GITMODULE"] = "ON"
        tc.variables["OPENMP"] = "OFF"
        # Upstream's test helpers hard-code the in-source build directory: rtest.py
        # uses bindir = "../build" relative to <src>/test and the doctests call
        # ../build/<tool>, which is exactly the ./build directory produced by the top
        # level Makefile.  cmake_layout builds out-of-source, so place the produced
        # artifacts in <source>/build as well and every upstream test file can stay
        # byte-identical.
        test_bindir = os.path.join(self.source_folder, "build")
        tc.variables["CMAKE_RUNTIME_OUTPUT_DIRECTORY"] = test_bindir
        tc.variables["CMAKE_LIBRARY_OUTPUT_DIRECTORY"] = test_bindir
        tc.variables["CMAKE_ARCHIVE_OUTPUT_DIRECTORY"] = test_bindir
        tc.generate()

    def _jobs(self):
        """Parallelism for the build tool.

        ``tools.build:jobs`` defaults to ``os.cpu_count()``, which over-reports on the
        OHOS device (20 vs. 8 usable cores) and would over-subscribe a machine that is
        shared with other builds.  This recipe therefore defaults to 2 (85 targets with
        a hard 3600 s build budget are uncomfortable at 1) and honours an explicit
        ``-c tools.build:jobs=N``.  The value is appended after the toolchain's default
        ``-j``; the last ``-j`` wins for GNU make.
        """
        conf_jobs = self.conf.get("tools.build:jobs", default=None, check_type=int)
        return conf_jobs if conf_jobs else 2

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=[f"-j{self._jobs()}"])
        # Upstream CTest suite (enable_testing() + add_pytest/add_pydoctest/add_doctest
        # in CMakeLists.txt; the WFA2 sub-project adds wfa2lib on top).
        #
        # Two of the registered tests are excluded here because their *test harness*
        # cannot work on OHOS.  Both are reported as NOT_RUN (never as passing) in the
        # task report; nothing is silently skipped:
        #   * vcfallelicprimitives - one of its doctest examples runs
        #     `diff <a> <b> | tail -6` through the shell and compares against output that
        #     was recorded with GNU diffutils (default "normal" format).  OHOS ships
        #     toybox diff in /system/bin, whose only output format is unified, and the
        #     OHOS Python prepends /system/bin:/usr/bin:/bin to PATH for every child, so
        #     the GNU diffutils binary from /data/service/hnp/bin is never reached.
        #     Verified: /system/bin/diff <a> <b> starts with "--- a/+++ b/@@".
        #   * wfa2lib - contrib/WFA2-lib/tests/wfa.utest.sh has a `#!/bin/bash -x`
        #     shebang; OHOS has no /bin/bash (the shell lives in
        #     /data/service/hnp/bin), so the kernel fails to start it (ctest BAD_COMMAND).
        #     The vendored third-party script is deliberately left untouched.
        env = Environment()
        env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        with env.vars(self).apply():
            self.run(
                f'ctest -E "{CTEST_EXCLUDE}"',
                cwd=self.build_folder,
                env=["conanbuild", "conanrun"],
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # Upstream installs the archives into ${CMAKE_INSTALL_BINDIR} (both vcflib and
        # WFA2 use ARCHIVE DESTINATION bin); move them to lib/ so that the package has
        # the conventional layout and cpp_info.libdirs.
        for archive in ("libvcflib.a", "libwfa2.a"):
            src = os.path.join(self.package_folder, "bin", archive)
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "lib")
                mkdir(self, dst_dir)
                os.replace(src, os.path.join(dst_dir, archive))

        # src/Variant.h includes <tabix.hpp>; the vendored tabixpp header is compiled
        # into libvcflib.a but upstream's install(FILES ${INCLUDES}) glob does not
        # cover contrib/tabixpp, so install it next to the other public headers.
        copy(
            self,
            "tabix.hpp",
            src=os.path.join(self.source_folder, "contrib", "tabixpp"),
            dst=os.path.join(self.package_folder, "include", "vcflib"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # vcflib is a static archive; WFA2 is a separate static archive that the
        # vendored legacy/vcf-wfa translation units reference.
        self.cpp_info.libs = ["vcflib", "wfa2"]
        self.cpp_info.includedirs = ["include/vcflib", "include/wfa2lib"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "vcflib")
        self.cpp_info.set_property("cmake_file_name", "libvcflib")
        self.cpp_info.set_property("cmake_target_name", "libvcflib::libvcflib")
        self.cpp_info.system_libs = ["m", "pthread"]
