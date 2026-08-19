#!/usr/bin/env python3
"""Conan recipe for libucontext 1.5.2 — ucontext implementation for musl-based OHOS.

Builds libucontext (getcontext/setcontext/swapcontext/makecontext) and
libucontext_posix via the upstream plain-Makefile build, then runs the
upstream test suite (make check) inside build().
"""

import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibucontextConan(ConanFile):
    name = "libucontext"
    version = "1.5.2"
    description = "ucontext implementation featuring glibc-compatible ABI"
    license = "ISC"
    homepage = "https://github.com/kaniini/libucontext"
    url = "https://github.com/kaniini/libucontext"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _make_env(self):
        # R33: get compiler/tools from Conan conf, never from shell env vars.
        # tools.build:compiler_executables is a dict; index it after reading.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"
        ar = compilers.get("ar") or "llvm-ar"
        ranlib = compilers.get("ranlib") or "llvm-ranlib"
        arch = "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
        return f"ARCH={arch} CC={cc} AR={ar} RANLIB={ranlib}"

    def build(self):
        apply_conandata_patches(self)
        # libucontext is an in-tree Makefile project; build in source folder.
        os.chdir(self.source_folder)
        # R9: -j1
        self.run(f"make {self._make_env()} -j1 all")
        # Upstream tests: test_libucontext / bare_posixabi / posix.
        self.run(f"make {self._make_env()} -j1 check")

    def package(self):
        os.chdir(self.source_folder)
        # 1.5.2 Makefile uses a prefix/libdir variable system (default /usr).
        # An empty prefix makes libdir=/lib, includedir=/include,
        # pkgconfigdir=/lib/pkgconfig; combined with DESTDIR these land in the
        # package folder. (LIBDIR=lib from 1.2 is ignored by this version.)
        self.run(
            f"make {self._make_env()} -j1 install "
            f"DESTDIR={self.package_folder}/ prefix="
        )
        # R26: default static build must not ship shared objects; otherwise
        # CMakeDeps links -lucontext dynamically while Conan provides no
        # runtime LD_LIBRARY_PATH for a static package, breaking the test.
        if not self.options.shared:
            for name in ("libucontext.so", "libucontext.so.1",
                         "libucontext_posix.so", "libucontext_posix.so.1"):
                path = os.path.join(self.package_folder, "lib", name)
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)

    def package_info(self):
        # libucontext (unprefixed ABI) and libucontext_posix (signal-aware).
        self.cpp_info.libs = ["ucontext", "ucontext_posix"]
