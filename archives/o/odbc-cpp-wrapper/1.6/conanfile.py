#!/usr/bin/env python3
"""Conan recipe — odbc-cpp-wrapper 1.6 (CMake)"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OdbcCppWrapperConan(ConanFile):
    name = "odbc-cpp-wrapper"
    version = "1.6"
    description = "SAP's C++ wrapper for ODBC API providing object-oriented database access"
    license = "Apache-2.0"
    homepage = "https://github.com/SAP/odbc-cpp-wrapper"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_odbc(self):
        """Ensure libiodbc is installed; discover ODBC paths."""
        config = shutil.which("iodbc-config")
        if not config:
            self.output.info("iodbc-config not found, installing libiodbc via cmd-pkgs...")
            subprocess.run(
                "curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/"
                "releases/download/pkgs/install.sh | sh -s -- libiodbc 3.52.16",
                shell=True, check=True, timeout=120
            )
            config = shutil.which("iodbc-config")
        if not config:
            self.output.warning("libiodbc installation failed; attempting standard discovery")
            return None, None
        cflags = subprocess.check_output(
            [config, "--cflags"], text=True
        ).strip()
        libs = subprocess.check_output(
            [config, "--libs"], text=True
        ).strip()
        include_dir = None
        lib_path = None
        for flag in cflags.split():
            if flag.startswith("-I"):
                include_dir = flag[2:]
        lib_dir = None
        for flag in libs.split():
            if flag.startswith("-L"):
                lib_dir = flag[2:]
            elif flag.startswith("-l") and "odbc" in flag[2:] and lib_dir:
                candidate = os.path.join(lib_dir, f"lib{flag[2:]}.so")
                if os.path.exists(candidate):
                    lib_path = candidate
        return include_dir, lib_path

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        include_dir, lib_path = self._ensure_odbc()
        if include_dir:
            tc.variables["ODBC_INCLUDE_DIR"] = include_dir
        if lib_path:
            tc.variables["ODBC_LIBRARY"] = lib_path
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
        self.cpp_info.libs = ["odbccpp"]
        # libiodbc is a system library installed via cmd-pkgs
        self.cpp_info.system_libs = ["iodbc", "iodbcinst"]
        self.cpp_info.set_property("cmake_file_name", "odbccpp")
        self.cpp_info.set_property("cmake_target_name", "odbccpp::odbccpp")
