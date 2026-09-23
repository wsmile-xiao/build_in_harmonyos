#!/usr/bin/env python3
"""Conan recipe for libahp-gt 1.7.3 - AHP GT telescope mount controllers.

libahp-gt drives the AHP GT (Skywatcher compatible) stepper controllers over a
serial port or UDP: stepping configuration, goto/tracking, RA/Dec <-> Alt/Az
conversions and a SynScan compatible server.

OHOS notes
----------
* Small CMake project (``CMakeLists.txt`` with ``cmake_minimum_required(2.6)``).
  The OHOS CMake is 3.27+, which rejects pre-3.5 minimums, so
  ``CMAKE_POLICY_VERSION_MINIMUM=3.5`` is injected (same approach as
  archives/l/libftdi).
* ``CMakeLists.txt`` calls ``execute_process(doxygen ...)``; the sandbox has no
  doxygen, but the call is not checked, so configuration continues.  The
  generated header ``ahp_gt.h`` lands in the build folder and is installed to
  ``include/ahp`` (upstream layout).
* No dependencies beyond libm/threads.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get

required_conan_version = ">=2.0"


class LibahpGtConan(ConanFile):
    name = "libahp-gt"
    version = "1.7.3"
    description = ("Library to drive AHP GT stepper controllers: stepping "
                   "configuration, goto/tracking, RA-Dec conversions")
    license = "MIT"
    homepage = "https://github.com/iliaplatone/libahp-gt"
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
                "libahp-gt OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # ahp_gt.c guards many int/double getters with a bare `return;` (the
        # pre-2020 gcc default only warns about -Wreturn-type, clang 15 makes it
        # an error in C).  Downgrade it back to a warning instead of editing
        # dozens of upstream lines; the affected getters are only meaningful
        # with a controller attached.
        toolchain.extra_cflags = ["-Wno-error=return-type"]
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["ahp_gt"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "ahp_gt")
        self.cpp_info.set_property("cmake_target_name", "ahp_gt::ahp_gt")
