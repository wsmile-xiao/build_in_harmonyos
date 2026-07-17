#!/usr/bin/env python3
"""Conan recipe for SIPp 3.7.7."""

import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file


class SippConan(ConanFile):
    name = "sipp"
    version = "3.7.7"
    description = "Traffic generator for the SIP protocol"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/SIPp/sipp"
    url = "https://github.com/SIPp/sipp"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        repo_root = os.path.abspath(os.path.join(self.recipe_folder, "..", "..", "..", ".."))
        ncurses_dir = os.path.join(repo_root, "archives", "n", "ncurses", "6.5")
        if os.path.isfile(os.path.join(ncurses_dir, "conanfile.py")):
            self.output.info("Exporting local dependency recipe: ncurses/6.5")
            conan_cmd = [shutil.which("conan")] if shutil.which("conan") else [sys.executable, "-m", "conan"]
            subprocess.run(conan_cmd + ["export", ncurses_dir], check=True)
        else:
            self.output.warning("local dependency recipe not found: ncurses/6.5")

    def requirements(self):
        self.requires("ncurses/6.5")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["USE_SSL"] = "OFF"
        tc.variables["USE_PCAP"] = "OFF"
        tc.variables["USE_SCTP"] = "OFF"
        tc.variables["USE_GSL"] = "OFF"
        tc.variables["BUILD_STATIC"] = False
        tc.variables["USE_ASAN"] = False

        ncurses = self.dependencies["ncurses"]
        if ncurses:
            include_dirs = []
            package_folder = ncurses.package_folder
            for include_dir in ncurses.cpp_info.includedirs:
                if not os.path.isabs(include_dir):
                    include_dir = os.path.join(package_folder, include_dir)
                include_dirs.append(include_dir)
                include_dirs.append(os.path.join(include_dir, "ncursesw"))
            lib_dirs = []
            for lib_dir in ncurses.cpp_info.libdirs:
                if not os.path.isabs(lib_dir):
                    lib_dir = os.path.join(package_folder, lib_dir)
                lib_dirs.append(lib_dir)
            for lib_dir in lib_dirs:
                for name in ("libncursesw.a", "libncursesw.so", "libcursesw.a", "libcursesw.so", "libncurses.a", "libncurses.so"):
                    candidate = os.path.join(lib_dir, name)
                    if os.path.exists(candidate):
                        tc.variables["CURSES_LIBRARY"] = candidate
                        break
                if "CURSES_LIBRARY" in tc.variables:
                    break
            for lib_dir in lib_dirs:
                for name in ("libtinfow.a", "libtinfow.so", "libtinfo.a", "libtinfo.so"):
                    candidate = os.path.join(lib_dir, name)
                    if os.path.exists(candidate):
                        tc.variables["TINFO_LIBRARY"] = candidate
                        break
                if "TINFO_LIBRARY" in tc.variables:
                    break
            tc.variables["CURSES_LIBRARY_INCLUDE_DIRS"] = ";".join(dict.fromkeys(include_dirs))

        default_prefix = os.environ.get("DEFAULT_PREFIX")
        if default_prefix:
            include_dir = os.path.join(default_prefix, "include")
            lib_dir = os.path.join(default_prefix, "lib")
            curses_library = os.path.join(lib_dir, "libncursesw.a")
            tinfo_library = os.path.join(lib_dir, "libtinfow.a")
            if not os.path.exists(tinfo_library):
                tinfo_library = os.path.join(lib_dir, "libtinfo.a")
            if os.path.exists(curses_library):
                tc.variables["CURSES_LIBRARY"] = curses_library
                if os.path.exists(tinfo_library):
                    tc.variables["TINFO_LIBRARY"] = tinfo_library
                tc.variables["CURSES_LIBRARY_INCLUDE_DIRS"] = ";".join([include_dir, os.path.join(include_dir, "ncursesw")])
        tc.generate()

    def build(self):
        cmake_lists = os.path.join(self.source_folder, "CMakeLists.txt")
        replace_in_file(
            self,
            cmake_lists,
            'if(CMAKE_SYSTEM_NAME STREQUAL "Linux" AND TINFO_LIBRARY)',
            'if((CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS") AND TINFO_LIBRARY)',
        )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "sipp", self.build_folder, os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(
            self,
            "*.xml",
            os.path.join(self.source_folder, "sipp_scenarios"),
            os.path.join(self.package_folder, "res", "sipp_scenarios"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
