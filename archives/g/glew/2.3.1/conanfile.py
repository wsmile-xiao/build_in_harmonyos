#!/usr/bin/env python3
"""Conan recipe for the static GLEW 2.3.1 library."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class GlewConan(ConanFile):
    name = "glew"
    version = "2.3.1"
    description = "The OpenGL Extension Wrangler Library"
    license = "BSD-3-Clause"
    homepage = "https://glew.sourceforge.net/"
    url = "https://github.com/nigels-com/glew"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "This adaptation provides the static GLEW archive; shared builds "
                "would require a platform OpenGL/EGL linker closure."
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or shutil.which("clang") or "clang"
        ar = compilers.get("ar") or shutil.which("llvm-ar") or "llvm-ar"
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        cflags = [
            "-O2",
            "-Wall",
            "-W",
            "-Iinclude",
            "-fPIC",
            "-Wcast-qual",
            "-std=c89",
            "-pedantic",
            "-fno-stack-protector",
            "-DGLEW_EGL",
        ]
        configured_flags = self.conf.get(
            "tools.build:cflags", default=[], check_type=list
        ) or []
        if isinstance(configured_flags, str):
            configured_flags = [configured_flags]
        cflags.extend(configured_flags)
        sysroot = self.conf.get("tools.build:sysroot", default=None)
        if sysroot:
            # Make executes recipes through the POSIX shell on Windows; escape
            # spaces so the sysroot remains one compiler argument.
            sysroot = str(sysroot).strip('"')
            cflags.append("--sysroot=" + sysroot.replace(" ", "\\ "))
        cflags_text = " ".join(cflags)

        # Build only the archive.  The upstream shared target links against the
        # platform GL/EGL implementation and is intentionally outside this
        # dependency-free static package.
        self.run(
            'make -C "{}" SYSTEM=linux-clang-egl CC="{}" AR="{}" '
            'STRIP= GLEW_NO_GLU=-DGLEW_NO_GLU GLEW_PREFIX=/ GLEW_DEST=/ '
            'LIBDIR=/lib TMPDIR="{}" CFLAGS="{}" glew.lib.static -j1'.format(
                self.source_folder, cc, ar, tmpdir, cflags_text
            )
        )

    def package(self):
        copy(
            self,
            "libGLEW.a",
            os.path.join(self.source_folder, "lib"),
            os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "*.h",
            os.path.join(self.source_folder, "include", "GL"),
            os.path.join(self.package_folder, "include", "GL"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE.txt",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "glew.pc",
            self.source_folder,
            os.path.join(self.package_folder, "lib", "pkgconfig"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["GLEW"]
        self.cpp_info.system_libs = ["EGL", "GLv4"]
        self.cpp_info.defines = ["GLEW_STATIC", "GLEW_EGL", "GLEW_NO_GLU"]
        self.cpp_info.set_property("cmake_file_name", "glew")
        self.cpp_info.set_property("cmake_target_name", "glew::glew")
