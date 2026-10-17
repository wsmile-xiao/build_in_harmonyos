#!/usr/bin/env python3
"""Conan recipe for zlib 1.3.1.1.1.1.1.

This suffix release keeps zlib static-only to avoid colliding with the system
libz.so, but builds libz.a from PIC objects so consumers may link it into DSOs
or Python extension modules.
"""

import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ZlibConan(ConanFile):
    name = "zlib"
    version = "1.3.1.1.1.1.1"
    description = "Massively-used data compression library (DEFLATE/inflate)."
    license = "Zlib"
    homepage = "https://zlib.net/"
    settings = "os", "compiler", "build_type", "arch"
    package_type = "static-library"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _detect_sysroot(self):
        """Extract --sysroot from the generated conanbuild.sh environment script.

        VirtualBuildEnv writes the profile's [buildenv] CFLAGS into a
        conanbuildenv-*.sh script sourced by conanbuild.sh.  We read both
        files to find the sysroot because the profile values are not
        injected into the Python process's os.environ.
        """
        import re
        gen = self.generators_folder
        # conanbuild.sh may source conanbuildenv-*.sh; read both.
        candidates = []
        main = os.path.join(gen, "conanbuild.sh")
        if os.path.isfile(main):
            candidates.append(main)
            try:
                with open(main) as fh:
                    for line in fh:
                        m = re.match(r'\.\s+"([^"]+)"', line.strip())
                        if m and os.path.isfile(m.group(1)):
                            candidates.append(m.group(1))
            except OSError:
                pass
        for path in candidates:
            try:
                with open(path) as fh:
                    content = fh.read()
                m = re.search(r"--sysroot=(\S+)", content)
                if m:
                    return m.group(1).rstrip('"').rstrip("'")
            except OSError:
                continue
        return ""

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        sysroot = self._detect_sysroot()
        # Include --sysroot in CFLAGS so zlib's configure and generated
        # Makefile both know where to find system headers and libraries.
        cflags = "-O2 -fPIC"
        if sysroot:
            cflags += f" --sysroot={sysroot}"
        config_shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run(
            'CONFIG_SHELL="{cs}" CC="{cc}" CFLAGS="{cf}" '
            '"{cs}" ./configure --static --prefix=/'.format(
                cs=config_shell, cc=cc, cf=cflags,
            )
        )
        self.run("make -j1")
        self.run("make check")

    def package(self):
        self.run("make install DESTDIR={}".format(self.package_folder))

    def package_info(self):
        self.cpp_info.libs = ["z"]
        self.cpp_info.set_property("pkg_config_name", "zlib")
        self.cpp_info.set_property("cmake_file_name", "zlib")
        self.cpp_info.set_property("cmake_target_name", "zlib::zlib")
