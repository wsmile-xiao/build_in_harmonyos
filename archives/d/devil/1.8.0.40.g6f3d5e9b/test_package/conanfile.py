#!/usr/bin/env python3
"""Conan test_package — devil/1.8.0.40.g6f3d5e9b (CI L1 consumer test).

Consumes the packaged devil (libIL + libILU) and runs a PNG/JPEG encode-decode
round-trip on the device, verifying the libpng/libjpeg wiring that the recipe
performs for src-IL.

OHOS note: the dynamic loader rejects unsigned ELF images, so the consumer
executable is self-signed with binary-sign-tool before it is executed (same
convention as the libpng test_package).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class DevilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _tool_in_compiler_dir(self, tool):
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict)
        for key in ("cpp", "c"):
            compiler = executables.get(key)
            if not compiler:
                continue
            compiler_dir = os.path.dirname(compiler)
            for candidate in (os.path.join(compiler_dir, tool),
                              os.path.join(compiler_dir, "llvm-" + tool)):
                if os.path.isfile(candidate):
                    return candidate
        return shutil.which(tool)

    def _sign_elf(self, path):
        if str(self.settings.os) != "OHOS" or not os.path.isfile(path):
            return
        signer = self._tool_in_compiler_dir("binary-sign-tool")
        if not signer:
            raise ConanException(
                "binary-sign-tool not found: required on OHOS because the "
                "dynamic loader rejects unsigned executables")
        readelf = self._tool_in_compiler_dir("readelf")
        objcopy = self._tool_in_compiler_dir("objcopy")
        tmp = "%s.signing-%s" % (path, os.getpid())
        shutil.copy2(path, tmp)
        try:
            if readelf and objcopy:
                sections = subprocess.run([readelf, "-S", tmp],
                                          capture_output=True, text=True,
                                          check=True).stdout
                if ".codesign" in sections:
                    subprocess.run([objcopy, "--remove-section",
                                    ".codesign", tmp], check=True)
            subprocess.run([signer, "sign", "-inFile", tmp, "-outFile", tmp,
                            "-selfSign", "1"], check=True)
            if readelf:
                sections = subprocess.run([readelf, "-S", tmp],
                                          capture_output=True, text=True,
                                          check=True).stdout
                if ".codesign" not in sections:
                    raise ConanException(f"signer did not add .codesign: {path}")
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # The consumer binary links the shared libIL/libILU (and transitive
        # conan deps), so it is executed directly under the "conanrun"
        # environment, which carries the runtime library paths. ctest would
        # spawn the process without that environment.
        executable = os.path.join(self.cpp.build.bindirs[0], "test_devil")
        self._sign_elf(executable)
        self.run(executable, env="conanrun")
