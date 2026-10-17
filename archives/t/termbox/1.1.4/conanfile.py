#!/usr/bin/env python3
"""Conan recipe for termbox 1.1.4 (plain Makefile terminal library)."""

import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class TermboxConan(ConanFile):
    name = "termbox"
    version = "1.1.4"
    description = "Simple terminal user-interface library for C and C++"
    license = "MIT"
    homepage = "https://github.com/termbox/termbox"
    url = "https://github.com/termbox/termbox"
    topics = ("terminal", "tui", "console", "input")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "termbox is supported only on Linux and OHOS"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = shlex.quote(compiler_executables.get("c", "clang"))
        ar = shlex.quote(compiler_executables.get("ar", "llvm-ar"))
        target = "libtermbox.so.1.0.0" if self.options.shared else "libtermbox.a"

        self.run(
            f"make CC={cc} AR={ar} -j1 {target}",
            cwd=self.source_folder,
        )

    def package(self):
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "termbox.h",
            self.source_folder,
            os.path.join(self.package_folder, "include"),
        )

        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            copy(
                self,
                "libtermbox.so.1.0.0",
                self.source_folder,
                libdir,
            )
            versioned_library = os.path.join(libdir, "libtermbox.so.1.0.0")
            if str(self.settings.os) == "OHOS":
                self._sign_ohos_elf(versioned_library)
            shutil.copy2(versioned_library, os.path.join(libdir, "libtermbox.so.1"))
            shutil.copy2(versioned_library, os.path.join(libdir, "libtermbox.so"))
        else:
            copy(self, "libtermbox.a", self.source_folder, libdir)

    def package_info(self):
        self.cpp_info.libs = ["termbox"]
        self.cpp_info.set_property("cmake_file_name", "termbox")
        self.cpp_info.set_property("cmake_target_name", "termbox::termbox")
        self.cpp_info.set_property("pkg_config_name", "termbox")

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        objcopy = shutil.which("llvm-objcopy") or (
            "/data/service/hnp/bin/llvm-objcopy"
        )
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            raise ConanInvalidConfiguration(
                "Required OHOS shared-library signing tools are missing"
            )
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            check=True,
            timeout=30,
        )
        subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                path,
                "-outFile",
                path,
                "-selfSign",
                "1",
            ],
            check=True,
            timeout=60,
        )
