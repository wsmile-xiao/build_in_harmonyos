#!/usr/bin/env python3
"""Consumer tests for RapidJSON 1.1.0."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class RapidjsonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning(
                "Cross-built RapidJSON consumers cannot run on this build host."
            )
            return

        if self.settings.os == "OHOS":
            self._sign_executables()
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

    def _sign_executables(self):
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        paths = [
            os.path.join(self.cpp.build.bindirs[0], name + suffix)
            for name in (
                "rapidjson_unit_consumer",
                "rapidjson_ohos_portability",
            )
        ]
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires llvm-objcopy and binary-sign-tool"
            )

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
