#!/usr/bin/env python3
"""Conan recipe — lss 1.0 (header-only, Linux Syscall Support).

lss (Linux Syscall Support) provides C language wrappers for making
direct Linux system calls. It is a header-only library — the main
artifact is linux_syscall_support.h. It is used by crashpad and
breakpad as a low-level dependency.

Adaptation for HarmonyOS:
  1. loff_t not defined in musl libc → patch adds typedef
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LssConan(ConanFile):
    name = "lss"
    version = "1.0"
    description = "Linux Syscall Support — direct Linux system call wrappers in C"
    license = "BSD-3-Clause"
    homepage = "https://chromium.googlesource.com/linux-syscall-support"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Header-only: no compilation, just apply patches
        apply_conandata_patches(self)

    def package(self):
        import os
        import shutil
        # Copy header file to include/
        include_dir = os.path.join(self.package_folder, "include")
        os.makedirs(include_dir, exist_ok=True)
        src_header = os.path.join(self.source_folder, "linux_syscall_support.h")
        if os.path.exists(src_header):
            shutil.copy2(src_header, os.path.join(include_dir, "linux_syscall_support.h"))
        else:
            raise Exception(f"Header not found at {src_header}")

    def package_id(self):
        self.info.clear()  # header-only: single package_id for all settings

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
