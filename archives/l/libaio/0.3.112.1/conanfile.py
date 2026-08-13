#!/usr/bin/env python3
"""Conan recipe for libaio 0.3.112.1 — Linux-native asynchronous I/O library.

Build system: plain Makefile (not autotools/cmake).
The Makefile delegates to src/Makefile for actual compilation.
Outputs: libaio.a (static), libaio.so.1.0.1 (shared, optional).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibaioConan(ConanFile):
    name = "libaio"
    version = "0.3.112.1"
    description = "Linux-native asynchronous I/O access library"
    license = "LGPL-2.1"
    homepage = "https://pagure.io/libaio"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars.
        # tools.build:compiler_executables is a dict like {"c": "...", "cpp": "..."}
        compilers = self.conf.get("tools.build:compiler_executables", check_type=dict) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        ranlib = compilers.get("ranlib", "llvm-ranlib")

        # R26: libaio is a system-name library — build static only to avoid
        # polluting /lib, /lib64 with shared libraries.
        enable_shared = "1" if self.options.shared else "0"

        # OHOS kernel triggers SIGSYS for io_pgetevents (syscall 292) instead
        # of returning -ENOSYS. Pass -DLIBAIO_NO_IO_PGETEVENTS to make the
        # patch undef __NR_io_pgetevents, falling through to the -ENOSYS stub.
        if self.settings.os == "OHOS":
            os.environ["CFLAGS"] = "-DLIBAIO_NO_IO_PGETEVENTS"

        # R9: Always use -j1.
        # The top-level Makefile delegates to src/Makefile via `make -C src`.
        # Command-line make variables (CC, AR, RANLIB, ENABLE_SHARED) are
        # automatically exported to sub-makes via MAKEFLAGS.
        # Use -C to point to source folder since build runs in a subfolder.
        self.run(f"make -C {self.source_folder} CC={cc} AR={ar} RANLIB={ranlib} ENABLE_SHARED={enable_shared} -j1")

    def package(self):
        # Copy built artifacts from src/ subdirectory.
        copy(self, "libaio.h", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include"))
        copy(self, "libaio.a", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            copy(self, "libaio.so*", os.path.join(self.source_folder, "src"),
                 os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # The -l flag for libaio is -laio, so the library name is "aio".
        self.cpp_info.libs = ["aio"]
        # libaio uses syscall() and __errno_location() from libc.
        self.cpp_info.system_libs = ["c"]
