#!/usr/bin/env python3
"""Conan recipe — usleep 20160311.094456 (plain Makefile).

usleep is a one-file C command-line wrapper of usleep(3):
`usleep <microseconds>` sleeps for that many microseconds and exits 0.

Version: upstream cpeuvrel/usleep-aur has no release or tag. 20160311.094456 is
the committer timestamp (UTC) of the master head commit 4f880a7a, pinned through
the official GitHub archive tarball of that commit (conandata.yml).

OHOS adaptation:
  - usleep.c only needs <stdlib.h> and <unistd.h>; musl declares usleep() in the
    default feature set, so the source builds unmodified (no patches).
  - The upstream Makefile hardcodes CC = gcc; CC is overridden on the make
    command line with the compiler from Conan conf (R33). Upstream CFLAGS
    (-Wall -Wextra -O2) are kept.
  - Upstream `make install` targets PREFIX=/usr/bin; package() copies the
    binary into bin/ instead.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class UsleepConan(ConanFile):
    name = "usleep"
    version = "20160311.094456"
    description = "Command-line wrapper of usleep(3): sleep for a number of microseconds"
    license = "MIT"
    homepage = "https://github.com/cpeuvrel/usleep-aur"
    url = "https://github.com/cpeuvrel/usleep-aur"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        # Upstream Makefile has no VPATH: build in the source tree.
        self.run(f'make -j1 CC="{cc}" usleep', cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "usleep", self.source_folder, os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
