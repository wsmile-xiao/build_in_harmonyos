#!/usr/bin/env python3
"""Conan recipe for ISMRMRD 1.15.0 on HarmonyOS PC.

ISMRMRD is the ISMRM Raw Data format library for MRI data (libismrmrd).
This recipe adapts upstream v1.15.0 to OpenHarmony / HarmonyOS PC (aarch64)
with the OHOS clang 15 toolchain.

OHOS adaptation notes
---------------------
1. Boost.Test header-only mode (patches 0001/0002). ``libboost_unit_test_framework``
   is not guaranteed to exist in the OHOS boost package (the boost/1.84~1.85
   recipes in this archive do not compile it at all) and upstream
   ``tests/CMakeLists.txt`` silently skips *all* tests when
   ``Boost_UNIT_TEST_FRAMEWORK_FOUND`` is false. Boost.Test is self-contained
   since 1.64 when ``BOOST_TEST_MODULE`` is defined in exactly one translation
   unit, so the tests are built header-only instead of being dropped.
2. Boost components (patch 0003) and Boost imported targets (patch 0004).
   Boost.Random has been header-only since 1.69 and the OHOS boost package
   exports no ``random`` component, so upstream's
   ``find_package(Boost ... random ... unit_test_framework)`` fails as a whole
   and leaves ``Boost_LIBRARIES`` empty -- but ``tests/test_dataset.cpp`` needs
   ``Boost.Filesystem``. The component list is narrowed to the two components
   the package really provides, and ``utilities/`` links the
   ``Boost::program_options`` imported target because CONFIG mode does not
   define the FindBoost-module variable ``Boost_PROGRAM_OPTIONS_LIBRARY``.
3. ``USE_HDF5_DATASET_SUPPORT=ON`` and ``BUILD_UTILITIES=ON``. Upstream only
   adds ``tests/test_dataset.cpp`` / ``tests/test_end_to_end.cpp`` to the test
   target when dataset support is on, and the two EndToEndTest cases shell out
   to ``utilities/ismrmrd_*`` binaries and abort with "Could not find utilities
   directory" when they are missing. Both are therefore kept on so that the
   complete upstream test set (54 cases) actually runs; the 1.7.0 recipe could
   disable HDF5 because its upstream test set did not cover that path.
4. Single-precision FFTW comes from ``fftw3f``, not ``fftw``. The utilities
   call ``fftwf_*`` and upstream's bundled ``cmake/FindFFTW.cmake`` requests the
   ``FLOAT_LIB`` component, but the OHOS ``fftw`` package is built with
   ``ENABLE_FLOAT=OFF`` (double precision only), so ``libfftw3f`` is taken from
   the separate ``fftw3f`` package.
5. ``pugixml`` target normalisation (patch 0003). Upstream links
   ``pugixml::static`` / ``pugixml::shared`` depending on ``BUILD_STATIC``; the
   Conan ``pugixml`` package exports only ``pugixml::pugixml``.
6. ``boost/1.90.0.4.1`` rather than 1.84/1.85: the older boost recipes pin
   ``zlib/1.3.1``, which conflicts with the ``zlib/1.3.1.1`` that
   ``hdf5/1.14.6`` pulls in.
7. ``-Wno-error=implicit-const-int-float-conversion``. Upstream appends
   ``-Wall -Werror`` to ``CMAKE_CXX_FLAGS``; clang 15 flags one benign upstream
   test pattern. Only that diagnostic is demoted, so every other warning stays
   fatal.
8. ``BUILD_EXAMPLES=OFF``: the C example is a demo, not a test case.
9. ``test_ismrmrd`` records its ``DT_NEEDED`` entry as the *relative* path
   ``../libismrmrd.so``, so the test binary only starts when the working
   directory is its own folder (this is how ctest runs it).

R28: test_package/ exists with two real consumers of the public API.
R36: all five requirements are published in the ohpcd registry.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class IsmrmrdConan(ConanFile):
    name = "ismrmrd"
    version = "1.15.0"
    description = "ISMRMRD - ISMRM Raw Data format library for MRI data"
    license = "MIT"
    homepage = "https://ismrmrd.github.io/"
    url = "https://github.com/ismrmrd/ismrmrd"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # boost >= 1.90 is required by the dependency graph: the older
        # boost/1.84.0 and boost/1.85.0 recipes pin zlib/1.3.1, which conflicts
        # with the zlib/1.3.1.1 pulled in by hdf5/1.14.6.
        self.requires("boost/1.90.0.4.1")
        self.requires("pugixml/1.16")
        self.requires("hdf5/1.14.6")
        # Upstream's bundled cmake/FindFFTW.cmake asks for the FLOAT_LIB
        # component, and the utilities call only fftwf_* symbols. The OHOS
        # fftw package builds with ENABLE_FLOAT=OFF (double precision only), so
        # the single-precision library comes from the separate fftw3f package;
        # without it find_package(FFTW COMPONENTS FLOAT_LIB) fails, utilities
        # are skipped and the two EndToEndTest cases abort.
        self.requires("fftw3f/3.3.10")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _abs_includedirs(self, dep):
        for inc in dep.cpp_info.includedirs:
            yield inc if os.path.isabs(inc) else os.path.join(dep.package_folder, inc)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS: conan maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS, but the CMake
        # platform file shipped in this SDK is Modules/Platform/OHOS.cmake --
        # there is no HarmonyOS.cmake. The name mismatch does not error out;
        # CMake just prints "System is unknown to cmake" and leaves a batch of
        # platform variables empty. The dangerous one is
        # CMAKE_SHARED_LIBRARY_SONAME_C_FLAG, whose emptiness drops
        # -Wl,-soname, from the link line: libismrmrd.so then has no DT_SONAME
        # and downstream recipes must link it by full path (the L5 SONAME gate
        # fails). The os guard is required -- setting this unconditionally
        # would override CMake's correct platform detection on non-OHOS
        # profiles.
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["BUILD_STATIC"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # No RPATH is baked in: the Conan run environment (see test_package's
        # VirtualRunEnv) provides LD_LIBRARY_PATH. This also keeps
        # `cmake --install` a plain file copy instead of an install-time ELF
        # RPATH rewrite, which is what the SONAME'd deliverables need in order
        # to stay loadable in the packaging step.
        tc.variables["CMAKE_SKIP_RPATH"] = "ON"
        tc.variables["USE_HDF5_DATASET_SUPPORT"] = "ON"
        tc.variables["BUILD_TESTS"] = "ON"
        # BUILD_UTILITIES must stay ON: the upstream EndToEndTest cases shell out
        # to utilities/ismrmrd_generate_cartesian_shepp_logan and friends and
        # abort with "Could not find utilities directory" when they are absent.
        tc.variables["BUILD_UTILITIES"] = "ON"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        # Boost.Test header-only mode: upstream's patched tests/CMakeLists.txt
        # uses this instead of find_package(Boost COMPONENTS unit_test_framework).
        boost = self.dependencies["boost"]
        tc.variables["BOOST_INCLUDE_DIR"] = next(self._abs_includedirs(boost))
        # Let CMake's FindHDF5 module locate the Conan hdf5 package.
        tc.variables["HDF5_ROOT"] = self.dependencies["hdf5"].package_folder
        # Upstream appends -Wall -Werror to CMAKE_CXX_FLAGS. clang 15 flags one
        # benign upstream-test pattern (tests/test_serialization.cpp divides by
        # RAND_MAX, an int constant that rounds when converted to float) as
        # -Wimplicit-const-int-float-conversion. Demote only that diagnostic
        # instead of dropping -Werror, so all other warnings stay fatal.
        hardening_flags = (
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE"
            " -Wno-error=implicit-const-int-float-conversion"
        )
        tc.variables["CMAKE_CXX_FLAGS"] = hardening_flags
        tc.variables["CMAKE_C_FLAGS"] = hardening_flags

        self._write_cmake_paths()
        tc.generate()

    def _write_cmake_paths(self):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.extend(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")',
                    ]
                )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        with self._runtime_env().vars(self).apply():
            cmake.build()
            self._run_upstream_tests()

    def _runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        # With CMAKE_SKIP_RPATH the build-tree test/utility binaries have no
        # RPATH, so the build folder itself (where libismrmrd.so lives) must be
        # on the loader path in addition to the usual output subdirectories.
        for rel in ("", "lib", "bin", os.path.join("libsrc", "bin")):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._runtime_env()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        home = os.path.join(self.build_folder, "test-home")
        os.makedirs(home, exist_ok=True)
        test_env.define("HOME", home)
        with test_env.vars(self).apply():
            # 1) ctest: upstream registers the single 'check' target; --no-tests=error
            #    guarantees a silently-skipped test set cannot pass CI.
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )
            # 2) Run the Boost.Test binary directly to surface the individual
            #    test-case count and the per-case result in the build log.
            #    The binary records DT_NEEDED as the *relative* path
            #    "../libismrmrd.so", so it must be started from its own
            #    directory (this is exactly how ctest invokes it).
            binary = self._find_test_binary()
            self.run(
                '"{}" --log_level=test_suite --report_level=detailed'.format(binary),
                cwd=os.path.dirname(binary),
            )

    def _find_test_binary(self):
        for candidate in glob.glob(
            os.path.join(self.build_folder, "**", "test_ismrmrd"), recursive=True
        ):
            if os.access(candidate, os.X_OK):
                return candidate
        raise ConanException("test_ismrmrd binary not found under the build folder")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["ismrmrd"]
        self.cpp_info.set_property("cmake_file_name", "ismrmrd")
        self.cpp_info.set_property("cmake_target_name", "ismrmrd::ismrmrd")
