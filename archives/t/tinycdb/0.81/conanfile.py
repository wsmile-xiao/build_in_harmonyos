#!/usr/bin/env python3
"""Conan recipe for tinycdb — CDB (Constant Data Base) library and tool."""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class TinycdbConan(ConanFile):
    name = "tinycdb"
    version = "0.81"
    description = "Small, fast, reliable constant database (CDB format) library and tool"
    license = "MIT"
    homepage = "https://www.corpit.ru/mjt/tinycdb/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_make_args(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        ranlib = compilers.get("ranlib", "llvm-ranlib")

        args = f"CC={cc} AR={ar} RANLIB={ranlib} CFLAGS=\"-fPIC -O2\""
        # R33: On OHOS, must use GNU ld (ld.bfd) instead of lld
        # Linker selectable via Conan conf (name like "bfd" or absolute path);
        # default "bfd" lets clang resolve ld.bfd via PATH
        if self.settings.os == "OHOS":
            ld = self.conf.get("user.tinycdb:ld", default="bfd")
            args += f' LDFLAGS="-fuse-ld={ld}"'
        return args

    def build(self):
        apply_conandata_patches(self)
        # R9: Always use -j1
        self.run(f"make {self._get_make_args()} -j1")

    def package(self):
        self.run(f"make {self._get_make_args()} "
                 f"prefix={self.package_folder} DESTDIR= install")

    def package_info(self):
        self.cpp_info.libs = ["cdb"]
        self.cpp_info.bindirs = ["bin"]
