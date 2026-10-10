#!/usr/bin/env python3
"""Conan test_package for libsbig/4.9.9 — L1 consumer test (R34/PF3).

The upstream libsbig is a prebuilt shared-library distribution whose
libsbig_arm64.bin is a *glibc* build (DT_NEEDED: libm.so.6 / libudev.so.1 /
libc.so.6 / ld-linux-aarch64.so.1).  OHOS uses musl libc and has no glibc
loader (only ld-musl-aarch64.so.1; libc soname is "libc.so"), so a runtime
dlopen/link-run of the delivered .so cannot succeed on OHOS — ELF signing
(binary-sign-tool) only clears the E318 "unsigned ELF rejected" gate, it does
not supply glibc symbols.

This test therefore verifies the package *statically*:
  - build(): CMake links a consumer against libsbig.so.4 — proves the header
    (sbigudrv.h) and the link contract (SONAME + exported symbols) are valid.
  - test():  runs check_elf.py over the delivered libsbig.so.4, asserting
    ET_DYN/AArch64, SONAME == libsbig.so.4, exported SBIGUnivDrvCommand, and
    DT_NEEDED libudev.so.1 (the eudev dependency contract).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibsbigTestConan(ConanFile):
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
        # R34/L0d: 字面 self.run 实际执行逻辑（非空壳）。test_package 根目录的
        # check_elf.py 对打包产物做静态 ELF 校验（SONAME/导出符号/NEEDED），
        # 不 dlopen/链接运行 glibc blob——OHOS musl 无 glibc loader（见文件头注释）。
        dep = self.dependencies["libsbig"]
        libdir = dep.cpp_info.libdirs[0]
        so = os.path.join(libdir, "libsbig.so.4")
        script = os.path.join(self.recipe_folder, "check_elf.py")
        self.run(f"python3 {script} {so}")

