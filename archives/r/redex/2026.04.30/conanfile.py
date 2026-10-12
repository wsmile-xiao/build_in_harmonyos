#!/usr/bin/env python3
"""Conan recipe for Redex 2026.04.30."""

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


class RedexConan(ConanFile):
    name = "redex"
    version = "2026.04.30"
    description = "Android bytecode optimizer"
    license = "MIT"
    homepage = "https://github.com/facebook/redex"
    url = "https://github.com/facebook/redex"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    default_options = {
        "boost/*:shared": True,
        "jsoncpp/*:shared": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.91.0.1.1")
        self.requires("jsoncpp/1.9.8")
        self.requires("zlib-ng-compat/2.3.3")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Redex is validated only for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        local_archive = os.environ.get("REDEX_SOURCE_ARCHIVE")
        if local_archive:
            if not os.path.isfile(local_archive):
                raise ConanInvalidConfiguration(
                    f"REDEX_SOURCE_ARCHIVE does not exist: {local_archive}"
                )
            check_sha256(
                self, local_archive, self.conan_data["sources"]["sha256"]
            )
            unzip(self, local_archive, strip_root=True)
            return
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TYPE"] = "Shared"
        # The published zlib-ng-compat package is static-only; keep Redex's
        # shared dependency mode while selecting its real libz.a artifact.
        tc.variables["ZLIB_USE_STATIC_LIBS"] = True
        tc.variables["CMAKE_CXX_STANDARD"] = 20
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        tc.variables["ZLIB_HOME"] = self.dependencies[
            "zlib-ng-compat"
        ].package_folder.replace("\\", "/")
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if not can_run(self):
            self.output.warning(
                "The target cannot run on this build host; executable checks "
                "must run on the native HarmonyOS validation worker."
            )
            return

        binary = self._find_build_binary("redex-all")
        self._sign_paths([binary], required=self.settings.os == "OHOS")
        self.run(
            shlex.join([binary, "--show-passes"]),
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
        binary = os.path.join(self.package_folder, "bin", "redex-all")
        self._sign_paths([binary], required=self.settings.os == "OHOS")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "bin")
        )

    def _find_build_binary(self, name):
        candidates = glob.glob(
            os.path.join(self.build_folder, "**", name), recursive=True
        )
        candidates = [
            path
            for path in candidates
            if os.path.isfile(path) and not os.path.islink(path)
        ]
        if len(candidates) != 1:
            raise ConanInvalidConfiguration(
                f"Expected one {name} build artifact, found {candidates}"
            )
        return candidates[0]

    def _sign_paths(self, paths, required):
        paths = [
            path
            for path in paths
            if os.path.isfile(path) and not os.path.islink(path)
        ]
        if not paths:
            return

        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            message = "HarmonyOS execution requires llvm-objcopy and binary-sign-tool"
            if required:
                raise ConanInvalidConfiguration(message)
            self.output.warning(message)
            return

        for path in paths:
            self._sign_elf_atomically(path, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(
                shlex.join([objcopy, "--remove-section", ".codesign", temporary])
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
