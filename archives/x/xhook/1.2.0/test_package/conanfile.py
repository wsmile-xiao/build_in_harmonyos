#!/usr/bin/env python3
"""Conan test_package — xhook 1.2.0.

Functional PLT-hook verification on the real OHOS runtime (mirrors the
upstream libtest/libbiz demo shipped in the xhookwrapper Android app):

- hook_target.c mirrors upstream libtest/jni/test.c: a shared library
  whose background thread calls malloc (a PLT call) in a loop.
- hook_main.c mirrors upstream libbiz/jni/biz.c: the consumer registers
  xhook_register(".*/libhooktarget\\.so$", "malloc", ...), calls
  xhook_refresh, then asserts the hook replacement function is actually
  invoked through the patched GOT, and that old_func captures the
  original malloc address.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class XhookTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.build_folder, "bin", "test_plt_hook")
            self.run('"{}"'.format(bin_path), env="conanrun")
