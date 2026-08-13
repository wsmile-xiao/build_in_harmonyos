#!/usr/bin/env python3
"""Conan test_package for sdl2_mixer 2.8.1 (library).

编译一个链接 libSDL2_mixer.a 的测试程序，调用 SDL_mixer API
（Mix_Init/Mix_OpenAudio），验证头文件与库可用。
OHOS 上 test 可执行文件必须先签名（binary-sign-tool），否则
运行报 Operation not permitted。
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Sdl2MixerTestConan(ConanFile):
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
        # OHOS ELF 必须签名，否则运行报 Operation not permitted
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
            # binary-sign-tool 输出的文件可能丢失可执行位，需恢复
            os.chmod(path, 0o755)

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_sdl2_mixer")
        assert os.path.isfile(test_bin), f"test binary not found: {test_bin}"
        try:
            r = subprocess.run([test_bin], capture_output=True, text=True, timeout=30)
            out = (r.stdout or "") + (r.stderr or "")
            print(f"test_sdl2_mixer: exit={r.returncode} out={out.strip()}")
            assert r.returncode == 0, f"test_sdl2_mixer failed: {out}"
        except PermissionError as e:
            raise AssertionError(f"test binary not executable (ELF 未签名?): {e}")
