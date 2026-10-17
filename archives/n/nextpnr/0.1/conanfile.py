#!/usr/bin/env python3
"""Conan recipe for nextpnr 0.1 (FPGA place & route) on OpenHarmony."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class NextpnrConan(ConanFile):
    name = "nextpnr"
    version = "0.1"
    description = "Portable FPGA place-and-route tool"
    license = "ISC"
    homepage = "https://github.com/YosysHQ/nextpnr"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    options = {
        "arch": ["ice40", "generic"],
        "build_heap": [True, False],
        "build_tests": [True, False],
    }
    default_options = {
        "arch": "ice40",
        "build_heap": True,
        "build_tests": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.91.0.1.3")
        if self.options.build_heap:
            self.requires("eigen/3.4.1")
        if self.options.arch == "ice40":
            # Provides share/icebox/chipdb-*.txt, the device database that
            # ice40/chipdb.py turns into a .bba at build time.
            self.requires("icestorm/1.1.1")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)

        # CMake 4.x removed compatibility with cmake_minimum_required(<3.5).
        # nextpnr 0.1 declares 3.5 itself but its vendored 3rdparty modules
        # (googletest 2.6.2, sanitizers-cmake 2.8) and pybind11 3.4 do not, so
        # configuring aborts before any compilation starts.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        # ARCH is mandatory in nextpnr -- there is no default architecture.
        tc.variables["ARCH"] = str(self.options.arch)

        # The GUI needs Qt5 (not published for OHOS) and BUILD_GUI also forces
        # BUILD_PYTHON on.  BUILD_PYTHON would need libpython plus pybind11.
        tc.variables["BUILD_GUI"] = "OFF"
        tc.variables["BUILD_PYTHON"] = "OFF"

        # tests/ is a git submodule (YosysHQ/nextpnr-tests) that the release
        # tarball does not contain, so BUILD_TESTS=ON can only ever produce a
        # test binary with zero cases.  Default OFF; see notes.md.
        tc.variables["BUILD_TESTS"] = "ON" if self.options.build_tests else "OFF"

        # IPO/LTO must be off: check_ipo_supported() enables
        # CMAKE_INTERPROCEDURAL_OPTIMIZATION, which the OHOS Clang 15 driver
        # does not support when linking the large generated chipdb objects.
        tc.variables["USE_IPO"] = "OFF"

        # BUILD_HEAP enables the analytic placer.  Its CMakeLists block is:
        #     find_package(Eigen3 REQUIRED NO_MODULE)
        #     include_directories(${EIGEN3_INCLUDE_DIRS})
        # NO_MODULE forces config mode, where CMakeDeps only defines the
        # imported target Eigen3::Eigen and never the legacy EIGEN3_INCLUDE_DIRS
        # variable, so include_directories() adds nothing and the build dies
        # with:  common/placer_heap.cc:37: fatal error: 'Eigen/Core' file not found
        # (same failure family as the Boost legacy variables in bba).  Supply
        # the variable from the dependency's own include directories.
        tc.variables["BUILD_HEAP"] = "ON" if self.options.build_heap else "OFF"
        if self.options.build_heap:
            eigen = self.dependencies["eigen"]
            eigen_includes = [
                os.path.join(eigen.package_folder, d)
                for d in eigen.cpp_info.includedirs
            ]
            tc.variables["EIGEN3_INCLUDE_DIRS"] = ";".join(eigen_includes)

        # nextpnr runs `git describe --tags --always` at configure time.  The
        # recipe builds from a release tarball, which is not a git checkout, so
        # the value has to be supplied or the command fails to produce one.
        tc.variables["CURRENT_GIT_VERSION"] = str(self.version)

        if self.options.arch == "ice40":
            icestorm_pkg = self.dependencies["icestorm"].package_folder
            tc.variables["ICEBOX_DATADIR"] = os.path.join(
                icestorm_pkg, "share", "icebox")

        # ── build-time generator runtime path ────────────────────────────────
        # bbasm is a build-machine executable: it is compiled during the build
        # and then *run* during the same build to turn chipdb-<dev>.bba into
        # chipdb-<dev>.cc.  ohpcd ships Boost as shared libraries only, and
        # CMake has no Platform module for HarmonyOS, so it never emits an
        # RPATH link option.  The linked bbasm therefore has no RUNPATH, cannot
        # locate libboost_program_options.so and friends, and every codegen
        # step dies with:
        #     Error loading shared library libboost_program_options.so
        #     Error relocating ... symbol not found
        #     make: *** [ice40/chipdb/chipdb-1k.cc] Error 127
        # Declaring the dependency library directories explicitly restores it.
        # extra_exelinkflags appends instead of overwriting the flags Conan
        # already set.
        rpaths = []
        for dep_name in ("boost",):
            dep = self.dependencies[dep_name]
            for libdir in dep.cpp_info.libdirs:
                rpaths.append(os.path.join(dep.package_folder, libdir))
        for path in rpaths:
            tc.extra_exelinkflags.append("-Wl,-rpath,%s" % path)
            tc.extra_sharedlinkflags.append("-Wl,-rpath,%s" % path)

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
