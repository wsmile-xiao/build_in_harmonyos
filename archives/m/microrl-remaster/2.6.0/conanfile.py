#!/usr/bin/env python3
"""Conan recipe — microrl-remaster 2.6.0 (custom clang build).

Micro Read Line library for small and embedded devices (C).
Upstream ships a single C source (src/microrl/microrl.c) plus headers and
example programs; there is no top-level configure/CMake build system, only an
examples/ Makefile (gcc). We compile the library source directly with the
Conan toolchain clang and archive with llvm-ar. Static by default.

Note: microrl_config.h #includes "microrl_user_config.h" unless
MICRORL_IGNORE_USER_CONFIGS is defined; the library compiles standalone with
its built-in defaults when that macro is set (upstream-supported escape hatch).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MicrorlRemasterConan(ConanFile):
    name = "microrl-remaster"
    version = "2.6.0"
    description = "Micro Read Line library for small and embedded devices"
    license = "Apache-2.0"
    homepage = "https://github.com/dimmykar/microrl-remaster"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
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
        self.folders.build = "."

    def source(self):
        # URL path ends with the tag (v2.6.0), so Conan cannot infer the
        # archive format from the URL suffix; name the file explicitly.
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="microrl-remaster-2.6.0.tar.gz")

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"
        ar = compilers.get("ar") or "llvm-ar"
        cflags = "-fPIC -O2 -std=gnu99 -I./src/include/microrl -DMICRORL_IGNORE_USER_CONFIGS"
        src = os.path.join(self.source_folder, "src", "microrl", "microrl.c")
        obj = os.path.join(self.source_folder, "microrl.o")
        self.run(f"{cc} {cflags} -c {src} -o {obj}", cwd=self.source_folder)
        if self.options.shared:
            self.run(
                f"{cc} -shared {obj} -o {os.path.join(self.source_folder, 'libmicrorl.so')}",
                cwd=self.source_folder,
            )
        else:
            self.run(
                f"{ar} rcs {os.path.join(self.source_folder, 'libmicrorl.a')} {obj}",
                cwd=self.source_folder,
            )

    def package(self):
        copy(self, "microrl.h", src=os.path.join(self.source_folder, "src", "include", "microrl"),
             dst=os.path.join(self.package_folder, "include", "microrl"))
        copy(self, "microrl_config.h", src=os.path.join(self.source_folder, "src", "include", "microrl"),
             dst=os.path.join(self.package_folder, "include", "microrl"))
        # microrl_config.h #includes "microrl_user_config.h" (unless
        # MICRORL_IGNORE_USER_CONFIGS); ship the upstream template under that
        # name as the default empty config so downstream consumers compile.
        copy(self, "microrl_user_config_template.h",
             src=os.path.join(self.source_folder, "src", "include", "microrl"),
             dst=os.path.join(self.package_folder, "include", "microrl"),
             keep_path=True)
        self.run("cp include/microrl/microrl_user_config_template.h include/microrl/microrl_user_config.h",
                 cwd=self.package_folder)
        copy(self, "libmicrorl.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libmicrorl.so", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["microrl"]
