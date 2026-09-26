#!/usr/bin/env python3
"""Conan recipe for RapidJSON 1.1.0, a header-only C++ JSON library."""

import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    copy,
    export_conandata_patches,
    get,
    unzip,
)


class RapidjsonConan(ConanFile):
    name = "rapidjson"
    version = "1.1.0.1"
    description = "A fast JSON parser/generator for C++ with both SAX and DOM style API"
    license = "MIT"
    homepage = "https://github.com/Tencent/rapidjson"
    url = "https://github.com/Tencent/rapidjson"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream unit tests (test/unittest) are gtest-based.
        self.requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        local_archive = os.environ.get("RAPIDJSON_SOURCE_ARCHIVE")
        if local_archive:
            if not os.path.isfile(local_archive):
                raise ConanInvalidConfiguration(
                    f"RAPIDJSON_SOURCE_ARCHIVE does not exist: {local_archive}"
                )
            check_sha256(
                self, local_archive, self.conan_data["sources"]["sha256"]
            )
            unzip(self, local_archive, strip_root=True)
            return
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["RAPIDJSON_BUILD_DOC"] = False
        tc.variables["RAPIDJSON_BUILD_EXAMPLES"] = False
        tc.variables["RAPIDJSON_BUILD_TESTS"] = True
        tc.variables["RAPIDJSON_BUILD_CXX11"] = True
        # CMake >= 4.0 removed compatibility with < 3.5 (knowledge E187).
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Upstream leaves CMAKE_INSTALL_DIR empty on systems that are
        # neither UNIX nor WIN32 (CMake does not classify HarmonyOS as
        # UNIX); CMake >= 4 rejects an empty install() DESTINATION.
        tc.variables["CMAKE_INSTALL_DIR"] = "lib/cmake/RapidJSON"
        tc.generate()
        # Explicit CMakeDeps: find_package(gtest CONFIG) in the upstream test
        # build needs the gtest-config.cmake that CMakeDeps generates.
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMAKE_POLICY_VERSION_MINIMUM must reach the cmake command line:
        # CMake >= 4.0 removed compatibility with < 3.5 (knowledge E187,
        # same as the cxxopts 3.2.0 recipe).
        cmake.configure(
            variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"}
        )
        cmake.build()

        if not can_run(self):
            self.output.warning(
                "The target cannot run on this build host; upstream tests "
                "must be executed by the native HarmonyOS validation worker."
            )
            return

        if self.settings.os == "OHOS":
            self._sign_build_artifacts()
        self.run(
            shlex.join(
                [
                    "ctest",
                    "--test-dir",
                    self.build_folder,
                    "--output-on-failure",
                    "--no-tests=error",
                ]
            ),
            env="conanrun",
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "license.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "rapidjson")
        self.cpp_info.set_property("cmake_target_name", "rapidjson::rapidjson")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []

    # HarmonyOS executable signing — same approach as the jsoncpp 1.9.8.1
    # recipe. Test binaries must be self-signed before ctest can run them.
    def _sign_build_artifacts(self):
        patterns = (os.path.join(self.build_folder, "**", "unittest"),)
        paths = []
        for pattern in patterns:
            paths.extend(glob.glob(pattern, recursive=True))
        self._sign_paths(paths, required=True)

    def _sign_paths(self, paths, required):
        paths = sorted(
            {
                path
                for path in paths
                if os.path.isfile(path) and not os.path.islink(path)
            }
        )
        if not paths:
            if required:
                raise ConanInvalidConfiguration(
                    "Signing is required but no artifacts were found to sign"
                )
            return

        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            message = (
                "HarmonyOS execution requires llvm-objcopy and binary-sign-tool"
            )
            if required:
                raise ConanInvalidConfiguration(message)
            self.output.warning(f"{message}; release worker must sign the package")
            return

        for path in paths:
            self._sign_elf_atomically(path, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(
                shlex.join(
                    [objcopy, "--remove-section", ".codesign", temporary]
                )
            )
            self.run(
                shlex.join(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        temporary,
                        "-outFile",
                        temporary,
                        "-selfSign",
                        "1",
                    ]
                )
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
        candidates = (
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        )
        return next((path for path in candidates if os.path.isfile(path)), "")
