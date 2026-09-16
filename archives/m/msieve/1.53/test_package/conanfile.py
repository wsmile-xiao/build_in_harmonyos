#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_package/conanfile.py — msieve 1.53

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class MsieveTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @staticmethod
    def _readelf():
        r = (
            shutil.which("llvm-readelf")
            or shutil.which("readelf")
        )
        if not r:
            raise ConanException("readelf not found for ELF verification")
        return r

    @classmethod
    def _check_elf(cls, path):
        """ELF64 AArch64 + musl 解释器 + .codesign 唯一 + 无 RPATH/宿主路径"""
        readelf = cls._readelf()
        run = lambda *a: subprocess.run(
            [readelf, *a], check=True, capture_output=True, text=True, timeout=60
        ).stdout

        fhdr = run("-h", path)
        if "ELF64" not in fhdr:
            raise ConanException(f"{path}: not ELF64")
        if "AArch64" not in fhdr:
            raise ConanException(f"{path}: machine is not AArch64")
        phdr = run("-l", path)
        if "/lib/ld-musl-aarch64.so.1" not in phdr:
            raise ConanException(f"{path}: musl interpreter PT_INTERP missing")

        shdr = run("-SW", path)
        if shdr.count(".codesign") != 1:
            raise ConanException(f"{path}: .codesign count != 1")

        dyn = run("-d", path)
        for bad in ("RPATH", "RUNPATH"):
            if bad in dyn:
                raise ConanException(f"{path}: {bad} present")
        for sec in (fhdr, phdr, shdr, dyn, run("-n", path), run("-s", path)):
            for host in ("/storage/", "/data/service/", "/home/", "/tmp/"):
                if host in sec:
                    raise ConanException(f"{path}: host path {host} leaked")

    def _locate_packaged_msieve(self):
        dep = self.dependencies["msieve"]
        p = os.path.join(dep.cpp_info.bindirs[0], "msieve")
        if not os.path.isfile(p):
            raise ConanException(f"packaged msieve binary not found: {p}")
        return p

    def test(self):
        # 消费者/功能测试（test_package.c）：真实分解 + 乘积回验 +
        # 独立素性复核 + 负向输入
        bin_dir = os.path.join(self.build_folder, self.cpp.build.bindirs[0])
        self.run(os.path.join(bin_dir, "msieve_test"), env="conanrun")

        # 鸿蒙特有测试（test_ohos.c）：目标机真实运行同一套分解验证
        self.run(os.path.join(bin_dir, "msieve_test_ohos"), env="conanrun")

        if self.settings.os == "OHOS":
            # 二进制格式断言：测试自身 ELF + 被测包 bin/msieve
            self._check_elf(os.path.join(bin_dir, "msieve_test"))
            self._check_elf(os.path.join(bin_dir, "msieve_test_ohos"))
            self._check_elf(self._locate_packaged_msieve())
