#!/usr/bin/env python3
"""Conan recipe for librsync 2.3.4."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import collect_libs, get, save


class LibrsyncConan(ConanFile):
    name = "librsync"
    version = "2.3.4"
    description = "Binary delta encoding library based on the rsync algorithm"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/librsync/librsync"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("librsync is adapted for Linux and OHOS")

    def requirements(self):
        self.requires("popt/1.16")

    def build_requirements(self):
        self.tool_requires("perl/5.42.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["BUILD_RDIFF"] = True
        tc.cache_variables["ENABLE_COMPRESSION"] = False
        tc.cache_variables["ENABLE_TRACE"] = False
        tc.cache_variables["USE_LIBB2"] = False
        tc.cache_variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.cache_variables["CMAKE_MODULE_PATH"] = self._popt_module_dir()
        if self.settings.os == "OHOS":
            tc.cache_variables["WIN_BASH"] = self._test_shell_command()
        if "fPIC" in self.options:
            tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
                self.options.fPIC
            )
        self._generate_find_popt()
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not cross_building(self):
            self.run(
                "ctest --output-on-failure",
                cwd=self.build_folder,
                env="conanbuild",
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "librsync")
        self.cpp_info.set_property("cmake_target_name", "librsync::librsync")
        self.cpp_info.set_property("pkg_config_name", "librsync")
        self.cpp_info.libs = collect_libs(self) or ["rsync"]
        if not self.options.shared:
            self.cpp_info.defines.append("LIBRSYNC_STATIC_DEFINE")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

    def _popt_module_dir(self):
        return os.path.join(self.generators_folder, "cmake-modules")

    def _test_shell_command(self):
        shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "sh"
        return "{};-e".format(shell)

    def _generate_find_popt(self):
        popt = self.dependencies["popt"]
        popt_folder = popt.package_folder
        include_dirs = self._dependency_dirs(
            popt_folder, popt.cpp_info.includedirs or ["include"]
        )
        lib_dirs = self._dependency_dirs(popt_folder, popt.cpp_info.libdirs or ["lib"])
        libs = list(popt.cpp_info.libs or ["popt"])
        library = self._find_popt_library(lib_dirs, libs[0])
        module = """set(POPT_FOUND TRUE)
set(POPT_INCLUDE_DIRS "{include_dirs}")
set(POPT_LIBRARIES "{library}")
if(NOT TARGET POPT::POPT)
    add_library(POPT::POPT UNKNOWN IMPORTED)
    set_target_properties(POPT::POPT PROPERTIES
        IMPORTED_LOCATION "{library}"
        INTERFACE_INCLUDE_DIRECTORIES "{include_dirs}")
endif()
""".format(include_dirs=";".join(include_dirs), library=library)
        save(self, os.path.join(self._popt_module_dir(), "FindPOPT.cmake"), module)

    def _find_popt_library(self, lib_dirs, lib_name):
        for lib_dir in lib_dirs:
            for filename in self._popt_library_filenames(lib_name):
                candidate = os.path.join(lib_dir, filename)
                if os.path.exists(candidate):
                    return candidate.replace("\\", "/")
        raise ConanInvalidConfiguration(
            "popt/1.16 was resolved but no popt library was found in {}".format(
                ", ".join(lib_dirs)
            )
        )

    def _popt_library_filenames(self, lib_name):
        if os.path.splitext(lib_name)[1]:
            return [lib_name]
        return [
            "lib{}.a".format(lib_name),
            "lib{}.so".format(lib_name),
            "{}.lib".format(lib_name),
        ]

    def _dependency_dirs(self, package_folder, paths):
        result = []
        for path in paths:
            if not os.path.isabs(path):
                path = os.path.join(package_folder, path)
            result.append(path.replace("\\", "/"))
        return result
