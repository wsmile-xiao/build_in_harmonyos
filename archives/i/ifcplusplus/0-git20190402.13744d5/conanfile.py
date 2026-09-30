#!/usr/bin/env python3
"""Conan recipe — ifcplusplus 0-git20190402.13744d5 (ifcquery/ifcplusplus).

IFC++ is an open source C++ library for reading and writing Industry
Foundation Classes (IFC) STEP files.

This version pins the upstream git snapshot 13744d58f9b99ce3b4d49567b7085917cd7a6a3c
(2019-04-02, "Merge pull request #143 from shenqiuyao/fix_random_crash").
Unlike 2.5, this snapshot does not vendor Boost: its public headers consume
boost::optional, boost::algorithm::string and boost::unordered, so the recipe
declares a real Conan dependency on the OHOS-adapted boost/1.84.0 package.

Only the static IfcPlusPlus library is packaged (the Qt viewer example is
not built), with the bundled Carve sources compiled in.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class IfcplusplusConan(ConanFile):
    name = "ifcplusplus"
    version = "0-git20190402.13744d5"
    description = "IFC++ - open source C++ library for IFC (Industry Foundation Classes) models"
    license = "MIT"
    homepage = "https://github.com/ifcquery/ifcplusplus"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # This snapshot's public headers use boost::optional / boost::algorithm::string
        # (ReaderUtil.h, StylesConverter.h, UnitConverter.cpp) and Carve uses
        # boost::unordered. Unlike 2.5 these are NOT vendored in-tree here.
        # transitive_headers=True because consumers include IFC++ headers that
        # themselves include Boost headers (same pattern as archives/n/numcpp).
        self.requires("boost/1.84.0", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Library package: do not build the Qt viewer example application.
        # This snapshot gates the example on BUILD_VIEWER_APPLICATION only
        # (there is no BUILD_CONSOLE_APPLICATION option in 13744d5).
        tc.variables["BUILD_VIEWER_APPLICATION"] = "OFF"
        tc.variables["BUILD_STATIC_LIBRARY"] = "OFF" if self.options.shared else "ON"
        # CMake does not recognize OHOS, inject Linux platform + armv8.
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "armv8"
        # CMake 4.x compatibility: upstream cmake_minimum_required(3.7.2) needs
        # an explicit policy floor on newer CMake versions.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Boost is consumed from the Conan package (headers only w.r.t. what
        # IFC++ uses), so point find_package(Boost) at the Conan package folder.
        boost_pkg = self.dependencies["boost"].package_folder
        tc.cache_variables["BOOST_ROOT"] = boost_pkg
        tc.cache_variables["Boost_NO_SYSTEM_PATHS"] = "ON"
        tc.cache_variables["Boost_INCLUDE_DIR"] = os.path.join(boost_pkg, "include")
        # OHOS musl does not provide pthread_setcancelstate(3). Boost.Core's
        # sp_thread_sleep.hpp guards those calls behind this opt-in macro (the
        # OHOS boost/1.84.0 recipe patches that guard in); without it the
        # boost::filesystem path pulled in by Carve fails to compile.
        tc.cache_variables["CMAKE_CXX_FLAGS"] = "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream sets CMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE in
        # IfcPlusPlus/CMakeLists.txt on non-Windows, which lands the static
        # archive under bin/; normalize it to the Conan convention lib/.
        bindir = os.path.join(self.package_folder, "bin")
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(bindir):
            os.makedirs(libdir, exist_ok=True)
            for name in os.listdir(bindir):
                if name.endswith(".a"):
                    shutil.move(os.path.join(bindir, name), os.path.join(libdir, name))

    def package_info(self):
        # Upstream builds Carve as a SHARED library whenever the compiler id is
        # GNU or Clang; this recipe patches it to STATIC (see patches/0001), so
        # both archives are delivered and both must be listed for linking.
        #
        # IFC++'s public headers include <boost/optional.hpp>,
        # <boost/algorithm/string.hpp>, <boost/unordered_map.hpp> and
        # <boost/uuid/uuid.hpp>, so consumers need Boost's include directory and
        # compile definitions too (the Boost package exposes those on its
        # `boost_headers` component — see archives/b/boost/1.84.0).
        self.cpp_info.libs = ["IfcPlusPlus", "carve"]
        self.cpp_info.requires = ["boost::boost_headers"]
