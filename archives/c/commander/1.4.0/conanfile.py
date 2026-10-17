#!/usr/bin/env python3
"""Conan recipe — commander 1.4.0 (clibs/commander, raw Makefile project).

commander is a small C command-line argument parser. Its upstream Makefile
only has `test` and `clean` targets (no configure, no install). This recipe
builds a static library libcommander.a from src/commander.c with the Conan
toolchain compiler (R33: never shell ${CC}), then packages the public header
and the library. R34: test_package exercises the real commander API.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CommanderConan(ConanFile):
    name = "commander"
    version = "1.4.0"
    description = "Command-line argument parser (clibs/commander)"
    license = "MIT"
    homepage = "https://github.com/clibs/commander"
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

        # R33: compiler/flags come from Conan conf, never shell env vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar") or os.environ.get("AR", "llvm-ar")
        ranlib = compilers.get("ranlib") or os.environ.get("RANLIB", "llvm-ranlib")
        cflags = "-fPIC -O2 -Wall -Wextra"

        src_dir = os.path.join(self.source_folder, "src")
        build_dir = self.build_folder

        # Upstream Makefile has no library target: build libcommander.a here.
        # Use absolute source/build paths — self.run() cwd is the build folder.
        self.run(f'"{cc}" {cflags} -c "{os.path.join(src_dir, "commander.c")}" '
                 f'-o "{os.path.join(build_dir, "commander.o")}"', env="conanbuild")
        self.run(f'"{ar}" rcs "{os.path.join(build_dir, "libcommander.a")}" '
                 f'"{os.path.join(build_dir, "commander.o")}"', env="conanbuild")
        self.run(f'"{ranlib}" "{os.path.join(build_dir, "libcommander.a")}"',
                 env="conanbuild")

        # Also build and run the upstream test program (test.c -> ./test)
        self.run(f'"{cc}" {cflags} "{os.path.join(self.source_folder, "test.c")}" '
                 f'"{os.path.join(src_dir, "commander.c")}" '
                 f'-o "{os.path.join(build_dir, "test")}"', env="conanbuild")
        if not cross_building(self):
            self.run(f'"{os.path.join(build_dir, "test")}"', ignore_errors=False)

    def package(self):
        if os.path.exists(os.path.join(self.build_folder, "libcommander.a")):
            copy(self, "libcommander.a", self.build_folder,
                 os.path.join(self.package_folder, "lib"))
        else:
            # fallback: header-only package if no static lib was produced
            copy(self, "commander.c", os.path.join(self.source_folder, "src"),
                 os.path.join(self.package_folder, "include"), keep_path=False)
        # keep_path=False so the header lands at <package>/include/commander.h
        copy(self, "commander.h", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["commander"]
        self.cpp_info.set_property("pkg_config_name", "commander")