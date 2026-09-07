#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibtommathConan(ConanFile):
    name = "libtommath"
    version = "1.3.0"
    description = "C library for number theoretic multiple-precision integers"
    license = "Unlicense"
    homepage = "https://github.com/libtom/libtommath"
    url = "https://github.com/libtom/libtommath"
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

    def _compiler_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return (
            executables.get("c", "clang"),
            executables.get("ar", "llvm-ar"),
            executables.get("ranlib", "llvm-ranlib"),
        )

    def validate(self):
        if self.options.shared:
            raise ConanInvalidConfiguration("libtommath 1.3.0 supports only static builds")

    def build(self):
        apply_conandata_patches(self)
        cc, ar, ranlib = self._compiler_tools()
        make_args = f"CC={cc} AR={ar} RANLIB={ranlib} -j1"
        self.run(f"make {make_args} test", cwd=self.source_folder)
        self.run(os.path.join(self.source_folder, "test"), cwd=self.source_folder)

    def package(self):
        copy(
            self,
            "tommath.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libtommath.a",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )

    def package_info(self):
        self.cpp_info.libs = ["tommath"]
