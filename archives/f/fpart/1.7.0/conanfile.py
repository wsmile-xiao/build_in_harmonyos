#!/usr/bin/env python3
"""Conan recipe — fpart 1.7.0 (Makefile)

File partition tool — sorts and packs files by size, count, or number of parts.
Includes fpsync for parallel directory synchronization using fpart.

Uses direct compilation instead of autotools to avoid aclocal/automake
dependency on CI workers that only have autoconf.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, chdir, copy
from conan.tools.layout import basic_layout


class FpartConan(ConanFile):
    name = "fpart"
    version = "1.7.0"
    description = "File partition tool — sort and pack files by size, count, or parts"
    license = "BSD-2-Clause"
    homepage = "http://contribs.martymac.org"
    url = "https://github.com/martymac/fpart"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        # Fix umask 077 issue on HMDFS (E011): directories created with
        # umask 077 get setgid bit which prevents file creation in config.status
        # Not needed for direct compilation, but kept for documentation
        src = self.source_folder
        cflags = "-fPIC -O2 -DEMBED_FTS -D_GNU_SOURCE -DHAVE_GETOPT_H -DHAVE_GETOPT_LONG"
        sources = [
            "src/utils.c", "src/options.c", "src/partition.c",
            "src/file_entry.c", "src/dispatch.c", "src/fts.c", "src/fpart.c",
        ]
        objects = [s.replace(".c", ".o") for s in sources]
        with chdir(self, src):
            # Compile each source file
            for src_file, obj_file in zip(sources, objects):
                self.run(f'clang {cflags} -Isrc -c {src_file} -o {obj_file}', env="conanbuild")
            # Link
            self.run(f'clang -o fpart {" ".join(objects)} -lm', env="conanbuild")

    def package(self):
        src = self.source_folder
        copy(self, "fpart", src=src, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "fpsync", src=os.path.join(src, "tools"), dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*.1", src=os.path.join(src, "man"), dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
