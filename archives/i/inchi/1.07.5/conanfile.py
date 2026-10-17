#!/usr/bin/env python3
"""Conan recipe for the IUPAC InChI API library 1.07.5."""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    get,
    replace_in_file,
    save,
)


class InchiConan(ConanFile):
    name = "inchi"
    version = "1.07.5"
    description = "IUPAC International Chemical Identifier API library"
    license = "IUPAC-InChI"
    homepage = "https://github.com/IUPAC-InChI/InChI"
    url = homepage
    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        patches = os.path.join(self.recipe_folder, "patches")
        if os.path.isdir(patches):
            copy(
                self,
                "*.patch",
                src=patches,
                dst=os.path.join(self.export_sources_folder, "patches"),
                keep_path=True,
            )

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"inchi supports Linux and OHOS package builds, got {self.settings.os}"
            )

    def build_requirements(self):
        self.test_requires("gtest/1.17.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

        root_cmake = os.path.join(self.source_folder, "CMakeLists.txt")
        replace_in_file(
            self,
            root_cmake,
            "include(FetchContent)\n"
            "FetchContent_Declare(\n"
            "    googletest\n"
            "    GIT_REPOSITORY https://github.com/google/googletest.git\n"
            "    GIT_TAG        v1.17.0\n"
            ")\n"
            "set(gtest_force_shared_crt ON CACHE BOOL \"\" FORCE)\n"
            "FetchContent_MakeAvailable(googletest)\n\n"
            "include(CTest)\n"
            "include(GoogleTest)\n"
            "enable_testing()",
            "option(INCHI_BUILD_TESTS \"Build the upstream unit tests\" ON)\n"
            "if(INCHI_BUILD_TESTS)\n"
            "    find_package(gtest CONFIG REQUIRED)\n"
            "    include(CTest)\n"
            "    enable_testing()\n"
            "endif()",
        )
        replace_in_file(
            self,
            root_cmake,
            "set(CMAKE_CXX_STANDARD 11)",
            "set(CMAKE_CXX_STANDARD 17)",
        )
        replace_in_file(
            self,
            root_cmake,
            "add_subdirectory(INCHI-1-SRC/INCHI_EXE/inchi-1/src)",
            "option(INCHI_BUILD_CLI \"Build the InChI command-line tool\" ON)\n"
            "if(INCHI_BUILD_CLI)\n"
            "    add_subdirectory(INCHI-1-SRC/INCHI_EXE/inchi-1/src)\n"
            "endif()",
        )
        replace_in_file(
            self,
            root_cmake,
            "add_subdirectory(INCHI-1-TEST/tests/test_unit)",
            "if(INCHI_BUILD_TESTS)\n"
            "    add_subdirectory(INCHI-1-TEST/tests/test_unit)\n"
            "endif()",
        )

        library_cmake = os.path.join(
            self.source_folder,
            "INCHI-1-SRC",
            "INCHI_API",
            "libinchi",
            "src",
            "CMakeLists.txt",
        )
        replace_in_file(
            self,
            library_cmake,
            "if(UNIX AND NOT APPLE)",
            "if(NOT WIN32 AND NOT APPLE)",
        )
        replace_in_file(
            self,
            library_cmake,
            'target_link_options(libinchi PRIVATE "LINKER:--version-script=${P_LIBINCHI_MAP}/libinchi.map,-z,relro")',
            'target_link_options(libinchi PRIVATE\n'
            '        "LINKER:--version-script=${P_LIBINCHI_MAP}/libinchi.map,-z,relro"\n'
            '        "LINKER:-soname,libinchi.so"\n'
            '    )',
        )

        test_dir = os.path.join(
            self.source_folder, "INCHI-1-TEST", "tests", "test_unit"
        )
        test_cmake = os.path.join(test_dir, "CMakeLists.txt")
        replace_in_file(
            self,
            test_cmake,
            "add_executable(${test_name} ${test_src})",
            "add_executable(${test_name} ${test_src} inchi_gtest_main.cpp)",
        )
        replace_in_file(
            self,
            test_cmake,
            "target_link_libraries(${test_name} PRIVATE gtest_main gmock_main test_dependencies libinchi)",
            "target_link_libraries(${test_name} PRIVATE gtest::gtest test_dependencies libinchi)",
        )
        save(
            self,
            os.path.join(test_dir, "inchi_gtest_main.cpp"),
            "#include <gtest/gtest.h>\n\n"
            "int main(int argc, char **argv)\n"
            "{\n"
            "    ::testing::InitGoogleTest(&argc, argv);\n"
            "    return RUN_ALL_TESTS();\n"
            "}\n",
        )

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["INCHI_BUILD_CLI"] = False
        tc.variables["INCHI_BUILD_TESTS"] = True
        tc.variables["CMAKE_SKIP_RPATH"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if can_run(self):
            test_env = Environment()
            test_env.prepend_path("LD_LIBRARY_PATH", self._build_libdir)
            with test_env.vars(self).apply():
                cmake.ctest(cli_args=["--output-on-failure"])
        else:
            self.output.warning(
                "Cross build compiled all seven upstream test executables; "
                "target execution is deferred to W3"
            )

    def package(self):
        package_libdir = os.path.join(self.package_folder, "lib")
        copy(
            self,
            "libinchi.so*",
            src=self._build_libdir,
            dst=package_libdir,
            keep_path=False,
        )
        library = os.path.join(package_libdir, "libinchi.so")
        if not os.path.isfile(library):
            raise ConanException(f"Expected shared library was not built: {library}")

        public_header_dir = os.path.join(
            self.source_folder, "INCHI-1-SRC", "INCHI_BASE", "src"
        )
        for header in ("inchi_api.h", "ixa.h"):
            copy(
                self,
                header,
                src=public_header_dir,
                dst=os.path.join(self.package_folder, "include"),
            )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["inchi"]
        self.cpp_info.set_property("cmake_file_name", "inchi")
        self.cpp_info.set_property("cmake_target_name", "inchi::inchi")
        self.cpp_info.set_property("pkg_config_name", "inchi")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

    @property
    def _build_libdir(self):
        return os.path.join(
            self.build_folder,
            "INCHI-1-SRC",
            "INCHI_API",
            "libinchi",
            "src",
            "lib",
        )
