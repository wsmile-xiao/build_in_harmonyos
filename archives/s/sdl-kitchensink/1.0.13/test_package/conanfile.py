#!/usr/bin/env python3
"""Conan test_package - sdl-kitchensink 1.0.13.

Links a small consumer against the package and runs it headless
(SDL_VIDEODRIVER=dummy), exercising the version/format/init API.
The test binary is an ELF executable: OHOS requires code signing before
running (binary-sign-tool), same approach as sdl2_image 2.6.0.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SdlKitchensinkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # OHOS: sign the ELF before it can be executed
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_sdl_kitchensink")
        self._sign_elf(test_bin)

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_sdl_kitchensink")
        if not os.path.isfile(test_bin):
            raise RuntimeError(f"test binary not found: {test_bin}")
        # Headless: no window/audio device in CI; kitchensink init uses SDL
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        self.run(f"'{test_bin}'", env="conanrun")

    def _sign_elf(self, path):
        if not os.path.isfile(path):
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null'.format(oc=objcopy, f=path), ignore_errors=True)
        tmp = path + ".signed"
        self.run('{sg} sign -inFile "{f}" -outFile "{t}" -selfSign 1'.format(sg=signer, f=path, t=tmp))
        if os.path.exists(tmp):
            shutil.move(tmp, path)
        os.chmod(path, 0o755)