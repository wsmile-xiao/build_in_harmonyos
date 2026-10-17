#!/usr/bin/env python3
"""Conan recipe for libsir 2.2.6 — custom Makefile (sircommon.mk) build.

libsir uses a hand-written Makefile (no configure script), so the
autotools template is replaced by a direct make invocation. The recipe
builds the static (libsir_s.a) and shared (libsir.so) libraries, the
example and the C/C++ test rigs; install() copies libs + headers into
the package prefix via the upstream install target (DESTDIR + PREFIX).

R26: system-name libraries default to static; package_type=library.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, chdir
from conan.tools.layout import basic_layout
import os


class LibsirConan(ConanFile):
    name = "libsir"
    version = "2.2.6"
    description = "libsir - a lightweight, cross-platform library for information distribution"
    license = "MIT"
    homepage = "https://github.com/aremmell/libsir"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libsir 2.2.6 has no forced third-party dependencies.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # The upstream Makefile is in the source folder (in-source build);
        # basic_layout uses a separate build dir, so run make in source_folder.
        # SHELL=/bin/sh avoids the broken `alias sh=sh` expansion on OHOS;
        # -j1 avoids the GNU make jobserver fifo, which HMDFS does not support.
        with chdir(self, self.source_folder):
            self.run("make -j1 SHELL=/bin/sh all", env="conanbuild")

    def package(self):
        # Upstream install uses DESTDIR+PREFIX; point it at the package folder.
        with chdir(self, self.source_folder):
            self.run(f"make -j1 SHELL=/bin/sh DESTDIR={self.package_folder} PREFIX=/ install",
                     env="conanbuild")
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "sir/**/*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["sir_s"]  # static lib is libsir_s.a
        if self.options.shared:
            self.cpp_info.libs = ["sir"]  # shared lib is libsir.so
        self.cpp_info.system_libs = ["dl", "pthread"]
        self.cpp_info.set_property("cmake_file_name", "libsir")
        self.cpp_info.set_property("cmake_target_name", "libsir::libsir")
