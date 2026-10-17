#!/usr/bin/env python3
"""Conan test_package for sdl2-image 2.8.12 (library).

Compile a small program linking libSDL2_image.a, call SDL_image APIs
(IMG_Init / IMG_Load_RW) and verify PNG/JPG/TIF/WEBP formats are wired.
OHOS: the test executable must be ELF-signed (binary-sign-tool) before it
can run, otherwise it fails with Operation not permitted. Runtime shared
deps (libtiff.so/libwebp.so) are provided by the conanrun env.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Sdl2ImageTestConan(ConanFile):
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
        self._sign_test_binary()

    def _sign_test_binary(self):
        bindir = os.path.join(self.cpp.build.bindirs[0])
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in os.listdir(bindir):
            path = os.path.join(bindir, f)
            if not os.path.isfile(path) or not os.access(path, os.X_OK):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null'.format(oc=objcopy, f=path), ignore_errors=True)
            tmp = path + ".signed"
            self.run('{sg} sign -inFile "{f}" -outFile "{t}" -selfSign 1'.format(sg=signer, f=path, t=tmp))
            if os.path.exists(tmp):
                shutil.move(tmp, path)
            # binary-sign-tool output may lose the exec bit; restore it
            os.chmod(path, 0o755)

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_sdl2_image")
        assert os.path.isfile(test_bin), f"test binary not found: {test_bin}"
        # headless run: use SDL dummy video driver
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        self.run("'{bin}'".format(bin=test_bin), env="conanrun")