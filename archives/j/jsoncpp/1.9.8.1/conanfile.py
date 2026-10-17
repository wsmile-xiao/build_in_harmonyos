#!/usr/bin/env python3
"""Conan recipe for JsonCpp 1.9.8.1 (R37 adaptation fix over published 1.9.8)."""

import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    copy,
    export_conandata_patches,
    get,
    unzip,
)


class JsonCppConan(ConanFile):
    name = "jsoncpp"
    version = "1.9.8.1"
    description = "C++ library for interacting with JSON"
    license = "MIT"
    homepage = "https://github.com/open-source-parsers/jsoncpp"
    url = "https://github.com/open-source-parsers/jsoncpp"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"JsonCpp is validated only for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        local_archive = os.environ.get("JSONCPP_SOURCE_ARCHIVE")
        if local_archive:
            if not os.path.isfile(local_archive):
                raise ConanInvalidConfiguration(
                    f"JSONCPP_SOURCE_ARCHIVE does not exist: {local_archive}"
                )
            check_sha256(
                self, local_archive, self.conan_data["sources"]["sha256"]
            )
            unzip(self, local_archive, strip_root=True)
            return
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        shared = bool(self.options.shared)
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = shared
        tc.variables["BUILD_STATIC_LIBS"] = not shared
        tc.variables["BUILD_OBJECT_LIBS"] = False
        tc.variables["JSONCPP_WITH_TESTS"] = True
        tc.variables["JSONCPP_WITH_POST_BUILD_UNITTEST"] = False
        tc.variables["JSONCPP_WITH_EXAMPLE"] = False
        tc.variables["JSONCPP_WITH_INSTALL"] = True
        tc.variables["JSONCPP_WITH_PKGCONFIG_SUPPORT"] = True
        tc.variables["JSONCPP_WITH_CMAKE_PACKAGE"] = True
        if not shared:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
                self.options.fPIC
            )

        if self.settings.os == "OHOS":
            # CMake has no built-in HarmonyOS platform module. Complete its
            # shared-linker contract so in-tree consumers record basename
            # SONAMEs and a build-only runtime path.
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
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
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
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        if self.settings.os == "OHOS" and self.options.shared:
            libraries = glob.glob(
                os.path.join(self.package_folder, "lib", "**", "*.so*"),
                recursive=True,
            )
            self._sign_paths(libraries, required=False)

    def package_info(self):
        self.cpp_info.libs = ["jsoncpp"]
        self.cpp_info.set_property("cmake_file_name", "JsonCpp")
        self.cpp_info.set_property("cmake_target_name", "JsonCpp::JsonCpp")
        self.cpp_info.set_property("pkg_config_name", "jsoncpp")

    def _sign_build_artifacts(self):
        patterns = (
            os.path.join(self.build_folder, "**", "jsoncpp_test"),
            os.path.join(self.build_folder, "**", "jsontestrunner_exe"),
            os.path.join(self.build_folder, "**", "libjsoncpp.so"),
        )
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
