#!/usr/bin/env python3
"""Conan recipe — libmpeg3 1.8.dfsg (GNU Make)."""

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
import os
import shutil


class Libmpeg3Conan(ConanFile):
    name = "libmpeg3"
    version = "1.8.dfsg"
    description = "MPEG-1/2 decoder library and command-line utilities"
    license = "GPL-2.0-or-later"
    homepage = "http://heroinewarrior.com/libmpeg3.php"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "*.patch", src=os.path.join(self.recipe_folder, "patches"), dst=os.path.join(self.export_sources_folder, "patches"))

    def requirements(self):
        self.requires("a52dec/0.7.4")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def validate(self):
        from conan.errors import ConanInvalidConfiguration
        if self.settings.os != "OHOS" or self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("libmpeg3 recipe supports OHOS/armv8 only")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        shutil.copy(os.path.join(self.source_folder, "mpeg3css_fake.c"), os.path.join(self.source_folder, "mpeg3css.c"))
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"
        dep = self.dependencies["a52dec"].package_folder
        flags = "-fPIC -O2 -I. -I{}/include/a52dec -Du_int32_t=uint32_t -D_FILE_OFFSET_BITS=64 -D_LARGEFILE_SOURCE -D_LARGEFILE64_SOURCE".format(dep)
        libs = "-lm -lpthread {}/lib/liba52.a".format(dep)
        self.run('make clean', cwd=self.source_folder, ignore_errors=True)
        self.run('make -j1 CC="{}" CFLAGS="{}" A52OBJS= A52DIR= LIBS="{}"'.format(cc, flags, libs), cwd=self.source_folder)

    def package(self):
        copy(self, "libmpeg3.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "mpeg3private.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        build_output = os.path.join(self.source_folder, "aarch64")
        os.makedirs(os.path.join(self.package_folder, "lib"), exist_ok=True)
        os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
        shutil.copy2(os.path.join(build_output, "libmpeg3.a"), os.path.join(self.package_folder, "lib", "libmpeg3.a"))
        for tool in ("mpeg3dump", "mpeg3peek", "mpeg3toc", "mpeg3cat"):
            shutil.copy2(os.path.join(build_output, tool), os.path.join(self.package_folder, "bin", tool))

    def package_info(self):
        self.cpp_info.libs = ["mpeg3"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["m", "pthread"]
