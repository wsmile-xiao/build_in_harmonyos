#!/usr/bin/env python3
"""Conan recipe — rw 0.9 (portable ISO C99 static/shared library)."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RwConan(ConanFile):
    name = "rw"
    version = "0.9"
    description = "Exact rank-width and rank-decomposition library for graphs"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/rankwidth/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("rw is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = executables.get("c") or str(self.settings.compiler)
        archiver = executables.get("ar")
        if not archiver and os.path.isabs(cc):
            candidate = os.path.join(os.path.dirname(cc), "llvm-ar")
            if os.path.isfile(candidate):
                archiver = candidate
        if not archiver:
            archiver = shutil.which("llvm-ar") or shutil.which("ar") or "llvm-ar"
        return shlex.quote(str(cc)), shlex.quote(str(archiver))

    def build(self):
        apply_conandata_patches(self)
        cc, archiver = self._tools()
        source = shlex.quote(os.path.join(self.source_folder, "rw.c"))
        obj = shlex.quote(os.path.join(self.build_folder, "rw.o"))
        cflags = "-std=c99 -O2"
        if self.options.shared or self.options.get_safe("fPIC", False):
            cflags += " -fPIC"
        self.run(f"{cc} {cflags} -c {source} -o {obj}")

        if self.options.shared:
            library = shlex.quote(os.path.join(self.build_folder, "librw.so"))
            self.run(f"{cc} -shared {obj} -o {library}")
        else:
            library = shlex.quote(os.path.join(self.build_folder, "librw.a"))
            self.run(f"{archiver} rcs {library} {obj}")

    def package(self):
        copy(
            self,
            "rw.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "librw.*",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["rw"]
        self.cpp_info.set_property("cmake_file_name", "rw")
        self.cpp_info.set_property("cmake_target_name", "rw::rw")
