#!/usr/bin/env python3
"""Conan recipe — flag 0.1.2

Go-style flag parsing for C programs (clibs/flag).
flagset_* / flag_* singleton API for parsing command-line flags.

Build system: plain Makefile (implicit rules), no configure.
The upstream Makefile only builds the test/example binaries; the library
itself is flag.c + flag.h. We compile flag.c into libflag.a directly and
install the public header, following the repo convention for simple C libs.

License: MIT (Copyright (c) 2015 TJ Holowaychuk)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class FlagConan(ConanFile):
    name = "flag"
    version = "0.1.2"
    description = "Go-style flag parsing for C programs"
    license = "MIT"
    homepage = "https://github.com/clibs/flag"
    url = "https://github.com/clibs/flag"  # 官方仓库地址

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # flag.c only uses standard C headers; no external dependencies
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: get compiler from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        if self.options.shared:
            # Shared build: compile flag.c into libflag.so (-fPIC, standard C99)
            self.run(f'{cc} -std=c99 -fPIC -O2 -shared flag.c -o libflag.so', cwd=self.source_folder)
        else:
            # Static build: compile flag.c into libflag.a (upstream Makefile has
            # no lib/install target; the library is flag.c + flag.h)
            self.run(f'{cc} -std=c99 -fPIC -O2 -c flag.c -o flag.o', cwd=self.source_folder)
            # R33: fixed archiver (llvm-ar is part of the OHOS toolchain); avoid
            # bare shell env vars like $AR which are empty on release workers
            self.run('llvm-ar rcs libflag.a flag.o', cwd=self.source_folder)

    def package(self):
        copy(self, "flag.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        if self.options.shared:
            copy(self, "libflag.so", src=self.source_folder, dst=os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libflag.a", src=self.source_folder, dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["flag"]
