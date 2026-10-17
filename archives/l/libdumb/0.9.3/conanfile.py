#!/usr/bin/env python3
"""Build the upstream DUMB 0.9.3 core with its original GNU Make rules."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.gnu import AutotoolsToolchain


class LibdumbConan(ConanFile):
    name = "libdumb"
    version = "0.9.3"
    package_type = "static-library"
    license = "DUMB"
    homepage = "https://dumb.sourceforge.net/"
    description = "IT, XM, S3M and MOD music decoder and renderer"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        env = tc.environment()
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        compiler = compilers.get("c") or shutil.which("clang")
        archiver = shutil.which("llvm-ar")
        if not compiler or not archiver:
            raise ConanInvalidConfiguration("clang and llvm-ar are required")
        env.define("CC", compiler)
        env.define("AR", archiver)
        tc.generate(env)

    def build(self):
        # Equivalent to the upstream interactive configuration without Allegro.
        save(self, os.path.join(self.source_folder, "make", "config.txt"),
             "include make/unix.inc\nALL_TARGETS := core core-headers\n")
        self.run('make -j2 CC="$CC" AR="$AR" '
                 'CFLAGS_RELEASE="$CPPFLAGS $CFLAGS -Iinclude" '
                 'CFLAGS_DEBUG="$CPPFLAGS $CFLAGS -Iinclude -DDEBUGMODE=1"',
                 cwd=self.source_folder, env="conanbuild")

    def package(self):
        copy(self, "libdumb.a", src=os.path.join(self.source_folder, "lib", "unix"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "dumb.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False,
             excludes="internal/*")
        copy(self, "licence.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["dumb"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "libdumb")
        self.cpp_info.set_property("cmake_target_name", "libdumb::libdumb")
        self.cpp_info.set_property("pkg_config_name", "dumb")
