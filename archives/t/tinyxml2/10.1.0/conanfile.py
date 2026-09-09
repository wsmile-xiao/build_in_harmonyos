#!/usr/bin/env python3
"""Conan recipe for tinyxml2 10.1.0 on HarmonyOS PC."""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class Tinyxml2Conan(ConanFile):
    name = "tinyxml2"
    version = "10.1.0"
    description = "Simple, small, efficient C++ XML parser"
    license = "Zlib"
    homepage = "https://github.com/leethomason/tinyxml2"
    url = ""
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os == "OHOS" and self.options.shared:
            missing = [path for path in self._signing_tools() if not os.path.isfile(path)]
            if missing:
                raise ConanInvalidConfiguration(
                    "Shared tinyxml2 on OHOS requires signing tools: "
                    + ", ".join(missing)
                )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["tinyxml2_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["tinyxml2_BUILD_TESTING"] = True
        toolchain.variables["BUILD_TESTING"] = True
        toolchain.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        if self.settings.os == "OHOS":
            for language in ("C", "CXX"):
                toolchain.variables[
                    f"CMAKE_SHARED_LIBRARY_SONAME_{language}_FLAG"
                ] = "-Wl,-soname,"
                toolchain.variables[
                    f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG"
                ] = "-Wl,-rpath,"
                toolchain.variables[
                    f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG_SEP"
                ] = ":"
                toolchain.variables[
                    f"CMAKE_SHARED_LIBRARY_RPATH_LINK_{language}_FLAG"
                ] = "-Wl,-rpath-link,"
            toolchain.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            if self.settings.os == "OHOS":
                self._sign_build_artifacts()
            self._run_upstream_tests()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if self.settings.os == "OHOS" and self.options.shared:
            self._sign_shared_libraries()

    def _signing_tools(self):
        return (
            "/data/service/hnp/bin/llvm-objcopy",
            "/data/service/hnp/bin/binary-sign-tool",
        )

    def _sign_shared_libraries(self):
        patterns = (
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        )
        self._sign_paths(patterns, required=False)

    def _sign_build_artifacts(self):
        patterns = (
            os.path.join(self.build_folder, "**", "xmltest"),
            os.path.join(self.build_folder, "**", "*.so"),
            os.path.join(self.build_folder, "**", "*.so.*"),
        )
        self._sign_paths(patterns, required=True)

    def _sign_paths(self, patterns, required):
        paths = sorted(
            {
                path
                for pattern in patterns
                for path in glob.glob(pattern, recursive=True)
                if os.path.isfile(path) and not os.path.islink(path)
            }
        )
        if required and not paths:
            raise ConanInvalidConfiguration(
                "HarmonyOS tests require signed build-tree ELF artifacts"
            )

        objcopy, signer = self._signing_tools()
        for path in paths:
            self.run(f'{objcopy} --remove-section .codesign "{path}"')
            self.run(
                f'{signer} sign -inFile "{path}" '
                f'-outFile "{path}" -selfSign 1'
            )

    def _run_upstream_tests(self):
        old_library_path = os.environ.get("LD_LIBRARY_PATH")
        build_library_path = os.pathsep.join(
            (self.build_folder, os.path.join(self.build_folder, "lib"))
        )
        os.environ["LD_LIBRARY_PATH"] = build_library_path + (
            os.pathsep + old_library_path if old_library_path else ""
        )
        try:
            self.run(
                f'ctest --test-dir "{self.build_folder}" '
                "--output-on-failure --no-tests=error"
            )
        finally:
            if old_library_path is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = old_library_path

    def package_info(self):
        self.cpp_info.libs = ["tinyxml2"]
        self.cpp_info.set_property("cmake_file_name", "tinyxml2")
        self.cpp_info.set_property("cmake_target_name", "tinyxml2::tinyxml2")
        self.cpp_info.set_property("pkg_config_name", "tinyxml2")
