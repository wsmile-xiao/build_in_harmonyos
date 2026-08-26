#!/usr/bin/env python3
"""Conan test_package for yaml-cpp 0.8.0.

Consumer-side L1 test: parse a YAML document, walk the node tree, emit it
back, and assert the round-trip semantics. Exercised by `conan create`.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class YamlCppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
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
            # Cross-build host cannot execute the target binary; compiling and
            # linking the consumer against the installed package is sufficient
            # evidence the package is consumable.
            self.output.warning(
                "Cross-building: only compile+link of the consumer is verified"
            )
            return

        # OHOS XPM requires exec'd ELFs to be code-signed before execution.
        if self.settings.os == "OHOS":
            self._sign_executable()

        cmake = CMake(self)
        cmake.test()

    # ------------------------------------------------------------------
    # OHOS code-signing (shared with the recipe; kept self-contained so the
    # test package does not depend on private helpers of the recipe class).
    # ------------------------------------------------------------------
    def _sign_executable(self):
        bindir = self.cpp.build.bindirs[0] if self.cpp.build.bindirs else "."
        exe = os.path.join(bindir, "test_yaml_cpp")
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires llvm-objcopy and "
                "binary-sign-tool"
            )
        self._sign_elf_atomically(exe, objcopy, signer)

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
        return next(
            (path for path in candidates if os.path.isfile(path)), "",
        )
