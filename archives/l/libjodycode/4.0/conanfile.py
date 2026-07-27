#!/usr/bin/env python3
"""Conan recipe for libjodycode — pure Makefile build system.

libjodycode is Jody Bruchon's universal utility function library.
It uses a plain Makefile (no configure script) with PREFIX/DESTDIR variables.
"""
import os
import shutil
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LibjodycodeConan(ConanFile):
    name = "libjodycode"
    version = "4.0"
    description = "Jody Bruchon's universal utility function library for string, hash, file system, and path operations"
    license = "MIT"
    homepage = "https://codeberg.org/jbruchon/libjodycode"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Makefile project — no configure script
        # SIMD is auto-disabled on non-x86_64 (aarch64)
        # Build only the target type to avoid linking confusion
        if self.options.shared:
            self.run("make sharedlib -j1")
        else:
            self.run("make staticlib -j1")

    def package(self):
        # Manual install since make install expects both shared and static libs
        lib_dir = os.path.join(self.package_folder, "lib")
        inc_dir = os.path.join(self.package_folder, "include")
        man_dir = os.path.join(self.package_folder, "share", "man", "man7")
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(inc_dir, exist_ok=True)
        os.makedirs(man_dir, exist_ok=True)
        # Install header and man page
        shutil.copy2("libjodycode.h", os.path.join(inc_dir, "libjodycode.h"))
        shutil.copy2("libjodycode.7", os.path.join(man_dir, "libjodycode.7"))
        if self.options.shared:
            # Install shared library + symlinks
            shutil.copy2("libjodycode.so.4.0", os.path.join(lib_dir, "libjodycode.so.4.0"))
            # Fix symlinks that may fail on HMDFS (R5)
            so_full = "libjodycode.so.4.0"
            so_major = "libjodycode.so.4"
            so_link = "libjodycode.so"
            for name in (so_major, so_link):
                path = os.path.join(lib_dir, name)
                if os.path.lexists(path):
                    os.remove(path)
                target = so_full if name == so_major else so_major
                os.symlink(target, path)
        else:
            # Install static library only
            shutil.copy2("libjodycode.a", os.path.join(lib_dir, "libjodycode.a"))

    def package_info(self):
        self.cpp_info.libs = ["jodycode"]
        # The library SONAME is libjodycode.so.4
        if self.settings.os in ("Linux", "OHOS"):
            if self.options.shared:
                self.cpp_info.system_libs = ["c"]
