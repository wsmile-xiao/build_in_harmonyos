#!/usr/bin/env python3
"""Conan recipe for PLplot 5.15.0."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file


class PlplotConan(ConanFile):
    name = "plplot"
    version = "5.15.0"
    description = "Cross-platform scientific plotting library"
    license = "LGPL-2.0-or-later"
    homepage = "https://plplot.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"plplot supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["ENABLE_DYNDRIVERS"] = False
        tc.variables["DEFAULT_NO_BINDINGS"] = True
        tc.variables["ENABLE_cxx"] = True
        tc.variables["DEFAULT_NO_DEVICES"] = True
        tc.variables["PLD_ps"] = True
        tc.variables["PLD_psc"] = True
        tc.variables["PLPLOT_TEST_DEVICE"] = "psc"
        tc.variables["BUILD_TEST"] = True
        tc.variables["TEST_DIFF"] = False
        tc.variables["PL_HAVE_QHULL"] = False
        tc.variables["WITH_CSA"] = False
        tc.variables["PL_HAVE_FREETYPE"] = False
        tc.variables["USE_RPATH"] = False
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["MATH_LIB"] = ""
        tc.generate()

    def build(self):
        if str(self.settings.os) == "OHOS":
            replace_in_file(
                self,
                os.path.join(self.source_folder, "plplot_test", "CMakeLists.txt"),
                'message(FATAL_ERROR "Internal build-system error; unable to determine platform.")',
                "set(PLATFORM UNIX)",
            )
            replace_in_file(
                self,
                os.path.join(self.source_folder, "cmake", "modules", "plplot.cmake"),
                """if(NOT WIN32_OR_CYGWIN)
  find_library(MATH_LIB NAMES m PATHS /usr/local/lib /usr/lib)
  if(NOT MATH_LIB)
    message(FATAL_ERROR "Cannot find required math library")
  endif(NOT MATH_LIB)
endif(NOT WIN32_OR_CYGWIN)""",
                "# OHOS: math lives in libc; MATH_LIB pre-seeded empty in conanfile.",
            )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING.LIB",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.includedirs = ["include", os.path.join("include", "plplot")]
        self.cpp_info.libs = ["plplotcxx", "plplot", "qsastime"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "plplot")
        self.cpp_info.set_property("cmake_target_name", "plplot::plplot")
        self.cpp_info.set_property("pkg_config_name", "plplot")
