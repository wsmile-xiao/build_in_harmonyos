#!/usr/bin/env python3
"""Conan recipe for Boost 1.90.0.1.1 compiled components."""

import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
)


class BoostConan(ConanFile):
    name = "boost"
    version = "1.90.0.1.1"
    description = "Boost C++ libraries with Morpheus-required compiled components"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = "https://github.com/boostorg/boost"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BOOST_INCLUDE_LIBRARIES"] = (
            "algorithm;atomic;container;circular_buffer;filesystem;format;math;"
            "program_options;property_tree;system;tokenizer"
        )
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_ICU"] = True

        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
            tc.variables["BOOST_INSTALL_NO_VERSIONED_LIBS"] = True
            tc.variables["BOOST_FILESYSTEM_DISABLE_STATX"] = True
            tc.variables["BOOST_FILESYSTEM_DISABLE_COPY_FILE_RANGE"] = True
            for language in ("C", "CXX"):
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_SONAME_{language}_FLAG"
                ] = "-Wl,-soname,"
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG"
                ] = "-Wl,-rpath,"
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG_SEP"
                ] = ":"
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_RPATH_LINK_{language}_FLAG"
                ] = "-Wl,-rpath-link,"
            tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE_1_0.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        if str(self.settings.os) != "OHOS" or not self.options.shared:
            return

        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning(
                "OHOS signing tools are unavailable; native validation must sign shared libraries."
            )
            return

        libraries = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True
        )
        for library in libraries:
            if os.path.islink(library):
                continue
            self._sign_elf_atomically(library, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(
                f'"{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1'
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")

    def _component_library(self, available_libraries, component, header_only=False):
        exact = f"boost_{component}"
        if exact in available_libraries:
            return exact
        matches = sorted(
            library
            for library in available_libraries
            if library.startswith(f"boost_{component}")
        )
        if not matches and not header_only:
            self.output.warning(
                f"Component '{component}': no library matching 'boost_{component}' found"
            )
        return matches[0] if matches else ""

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Boost")
        self.cpp_info.includedirs = ["include"]
        available_libraries = set(collect_libs(self))

        for name in ("headers",):
            component = self.cpp_info.components[name]
            component.includedirs = ["include"]
            component.set_property("cmake_target_name", f"Boost::{name}")

        for name in ("atomic", "container", "filesystem", "format", "program_options", "system"):
            component = self.cpp_info.components[name]
            component.includedirs = ["include"]
            library = self._component_library(
                available_libraries, name, header_only=name in ("format", "system")
            )
            if library:
                component.libs = [library]
            component.set_property("cmake_target_name", f"Boost::{name}")

        self.cpp_info.components["filesystem"].requires = ["atomic", "system"]
        self.cpp_info.components["program_options"].requires = [
            "container",
            "headers",
        ]
