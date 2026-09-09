#!/usr/bin/env python3
"""Conan recipe for hoedown — standards compliant, fast, secure Markdown
processing library in C (ISC license).

hoedown builds with the upstream plain Makefile (no configure): the `all`
target produces libhoedown.a, libhoedown.so.3 (plus .so symlink) and the
`hoedown` / `smartypants` command-line tools.
"""
import os
import shlex

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, mkdir
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class HoedownConan(ConanFile):
    name = "hoedown"
    version = "3.0.7"
    description = "Standards compliant, fast, secure Markdown processing library in C"
    license = "ISC"
    homepage = "https://github.com/hoedown/hoedown"
    url = "https://github.com/hoedown/hoedown"

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

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # hoedown has no configure script: the plain Makefile is driven
        # directly. The upstream Makefile assigns its own CFLAGS (a Makefile
        # assignment overrides environment variables), so the toolchain
        # CFLAGS/LDFLAGS are passed explicitly on the make command line.
        with VirtualBuildEnv(self).vars().apply():
            cflags = os.environ.get("CFLAGS", "")
            ldflags = os.environ.get("LDFLAGS", "")
        cmd = "make -j1"
        if cflags:
            cmd += f" CFLAGS={shlex.quote(cflags)}"
        if ldflags:
            cmd += f" LDFLAGS={shlex.quote(ldflags)}"
        self.run(cmd, cwd=self.source_folder, env="conanbuild")

    def package(self):
        # Replicate the upstream `make install` layout (PREFIX=usr/local)
        # without depending on the coreutils `install` binary, which is not
        # present on every build host. The upstream Makefile always builds
        # both libhoedown.a and libhoedown.so.3; install the artifact that
        # matches the shared option so consumers link against exactly one.
        libdir = os.path.join(self.package_folder, "lib")
        bindir = os.path.join(self.package_folder, "bin")
        incdir = os.path.join(self.package_folder, "include", "hoedown")
        mkdir(self, libdir)
        mkdir(self, bindir)
        mkdir(self, incdir)
        if self.options.shared:
            copy(self, "libhoedown.so.3", self.source_folder, libdir)
            if not os.path.lexists(os.path.join(libdir, "libhoedown.so")):
                os.symlink("libhoedown.so.3", os.path.join(libdir, "libhoedown.so"))
        else:
            copy(self, "libhoedown.a", self.source_folder, libdir)
        copy(self, "hoedown", self.source_folder, bindir)
        copy(self, "smartypants", self.source_folder, bindir)
        copy(self, "*.h", os.path.join(self.source_folder, "src"), incdir)

    def package_info(self):
        self.cpp_info.libs = ["hoedown"]
        # The package also installs the hoedown/smartypants CLI tools into
        # bin/ (R38: commands.json declared at software level); exposing
        # bindirs keeps the recipe's static signal consistent with that.
        self.cpp_info.bindirs = ["bin"]
