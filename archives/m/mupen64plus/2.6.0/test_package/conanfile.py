#!/usr/bin/env python3
"""Conan test_package - mupen64plus 2.6.0.

Consumer-view validation of the N64 emulator core API, executed on the
device: version negotiation, full CoreStartup lifecycle (config system +
memory base + ROM database + embedded SDL init), state machine query,
ROM open (in-memory buffer: header parse + byteswap + MD5 + CIC detect),
ROM settings API contract, ROM close, defensive input validation and
CoreShutdown teardown. A synthetic minimal N64 ROM (valid 0x80371240
big-endian magic + entrypoint + name) is generated in C, no external
assets needed.

The test binary is an ELF executable: OHOS requires code signing before
running (binary-sign-tool), same approach as sdl-kitchensink 1.0.13 /
sdl2_image 2.6.0. Headless: SDL symbols are statically linked into the
core library and only initialized internally; no display is required.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Mupen64plusTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_mupen64plus")
        self._sign_elf(test_bin)

    def generate(self):
        # The core library (and its statically-linked C++ bits) needs
        # libc++_shared.so at runtime; expose the platform C++ runtime dir
        # that the conan-run env does not include by default on OHOS.
        from conan.tools.env import Environment
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.vars(self).save_script("system_run_env")

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_mupen64plus")
        if not os.path.isfile(test_bin):
            raise RuntimeError(f"test binary not found: {test_bin}")
        # The test chdir()s into a writable work dir (frontend requires a
        # writable ConfigPath/DataPath); run from the build folder.
        self.run(f"cd '{self.build_folder}' && '{test_bin}'",
                 env=["conanrun", "system_run_env"])

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
