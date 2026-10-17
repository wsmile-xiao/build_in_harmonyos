#!/usr/bin/env python3
"""Conan recipe for librepfunc 1.11.2 (raw Makefile project, no configure).

librepfunc is a C++ utility library built by a hand-written Makefile:
  - default target builds librepfunc.so.1.11.2 (shared)
  - `install-static` builds and installs librepfunc.a
No configure script exists, so a raw-makefile recipe is used (R33:
compiler executables come from the Conan toolchain conf, never bare
shell environment variables).
"""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibrepfuncConan(ConanFile):
    name = "librepfunc"
    version = "1.11.2"
    description = "librepfunc - a collection of common functions, classes and tools (VDR portal)"
    license = "MIT"
    homepage = "https://github.com/wirbel-at-vdr-portal/librepfunc"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("librepfunc is supported only on Linux/OHOS")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # Raw Makefile project: build in-place in the source folder
        # (basic_layout would place the build in a subfolder where the
        # Makefile does not exist).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _toolchain_compilers(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        if compilers:
            return {
                "cxx": compilers.get("cxx", "clang++"),
                "cc": compilers.get("c", "clang"),
            }
        return {"cxx": "clang++", "cc": "clang"}

    def build(self):
        apply_conandata_patches(self)
        t = self._toolchain_compilers()
        make_vars = "CXX={cxx} CC={cc} AR=llvm-ar RANLIB=llvm-ranlib".format(**t)
        self.run("make -j1 {0}".format(make_vars))

    def package(self):
        t = self._toolchain_compilers()
        make_vars = "CXX={cxx} CC={cc} AR=llvm-ar RANLIB=llvm-ranlib".format(**t)
        # Upstream Makefile uses lowercase `prefix` (not PREFIX). An empty
        # `prefix=` installs lib/include directly under the Conan package
        # root. pkgconfigdir is hardcoded to /usr/lib/pkgconfig, so the .pc
        # lands under usr/ — harmless auxiliary metadata.
        if self.options.shared:
            self.run("make install {0} DESTDIR={1} prefix=".format(make_vars, self.package_folder))
        else:
            self.run("make install-static {0} DESTDIR={1} prefix=".format(make_vars, self.package_folder))

    def package_info(self):
        # Library file is librepfunc.a / librepfunc.so.* -> -lrepfunc
        self.cpp_info.libs = ["repfunc"]
