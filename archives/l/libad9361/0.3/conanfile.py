#!/usr/bin/env python3
"""Conan recipe for libad9361 0.3 - AD9361 RF transceiver helper library.

libad9361 contains the helper routines used by the Linux IIO AD936x drivers:
RF clock chain calculation, FIR filter design (remex/remez), baseband auto-rate
selection, multi-chip sync and FMComms5 phase sync.  It talks to the chip
through libiio.

OHOS notes
----------
* Plain CMake C project depending on libiio (``find_library(iio)`` /
  ``find_path(iio.h)``).  The Conan ``libiio`` paths are injected as the
  corresponding cache variables so the project's search is satisfied.
* ``cmake_minimum_required(2.8.12)`` is rejected by CMake >= 3.27, so
  ``CMAKE_POLICY_VERSION_MINIMUM=3.5`` is injected.
* The project defines ``_GNU_SOURCE`` only when ``CMAKE_SYSTEM_NAME`` matches
  "Linux"; on OHOS it is HarmonyOS, so ``-D_GNU_SOURCE=1`` is added explicitly.
* Five upstream tests are built; only ``FilterDesignerTest`` and
  ``GenerateRatesTest`` are hardware-free (pure computation) and are run.
  ``filter_designer_hw``/``auto_rate_test_hw``/``fmcomms5_sync_test`` need a
  real AD936x over libiio.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import copy, get

required_conan_version = ">=2.0"

_HW_FREE_TESTS = ("FilterDesignerTest", "GenerateRatesTest")


class Libad9361Conan(ConanFile):
    name = "libad9361"
    version = "0.3"
    description = ("Helper library for the AD9361/AD9364 RF transceivers: RF clock "
                   "chain, FIR filter design, auto-rate, multi-chip sync (via libiio)")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/analogdevicesinc/libad9361-iio"
    url = ""

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libad9361 OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def requirements(self):
        self.requires("libiio/0.25")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        dependency = self.dependencies["libiio"]
        include_dir = os.path.join(dependency.package_folder,
                                   dependency.cpp_info.includedirs[0])
        lib_dir = os.path.join(dependency.package_folder,
                               dependency.cpp_info.libdirs[0])
        lib_file = os.path.join(lib_dir, "libiio.so")

        toolchain = CMakeToolchain(self)
        toolchain.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # The project uses find_library/find_path; give them the answers.
        toolchain.cache_variables["LIBIIO_INCLUDEDIR"] = include_dir
        toolchain.cache_variables["LIBIIO_LIBRARIES"] = lib_file
        # _GNU_SOURCE is only defined for CMAKE_SYSTEM_NAME "Linux".
        toolchain.extra_cflags = ["-D_GNU_SOURCE=1"]
        # OHOS CMake does not give the shared library a SONAME, so the test
        # binaries record a relative NEEDED ("../libad9361.so") that the loader
        # cannot resolve.  Force a plain SONAME.
        toolchain.cache_variables["CMAKE_SHARED_LINKER_FLAGS"] = "-Wl,-soname,libad9361.so"
        toolchain.generate()

        # The upstream tests link the shared libad9361/libiio; make them
        # findable when they run from the test source directory.
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", lib_dir)
        env.prepend_path("LD_LIBRARY_PATH", self.build_folder)
        env.vars(self).save_script("libad9361_runtime")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        test_dir = os.path.join(self.source_folder, "test")
        for name in _HW_FREE_TESTS:
            binary = os.path.join(self.build_folder, "test", name)
            self.run('"{}"'.format(binary), cwd=test_dir, env="conanbuild")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["ad9361"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = ["libiio::libiio"]
        self.cpp_info.set_property("cmake_file_name", "ad9361")
        self.cpp_info.set_property("cmake_target_name", "ad9361::ad9361")
        self.cpp_info.set_property("pkg_config_name", "libad9361")
