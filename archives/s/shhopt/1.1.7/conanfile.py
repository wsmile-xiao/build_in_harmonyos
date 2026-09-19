#!/usr/bin/env python3
"""Conan recipe — shhopt 1.1.7 (Makefile)"""

import os
import shlex
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


class ShhoptConan(ConanFile):
    name = "shhopt"
    version = "1.1.7"
    description = "C library for parsing short and GNU-style command-line options"
    license = "Artistic-1.0"
    homepage = "https://shh.thathost.com/pub-unix/"
    url = "https://shh.thathost.com/pub-unix/"
    topics = ("options", "command-line", "parser", "c")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os != "OHOS" or self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "shhopt is packaged for HarmonyOS PC aarch64"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        copy(self, "Makefile", src=self.source_folder, dst=self.build_folder)
        copy(self, "shhopt.c", src=self.source_folder, dst=self.build_folder)
        copy(self, "shhopt.h", src=self.source_folder, dst=self.build_folder)

        executables = self.conf.get("tools.build:compiler_executables", default={})
        cc = executables.get("c", "clang")
        optimization = "-O0 -g" if self.settings.build_type == "Debug" else "-O2"
        pic = "-fPIC" if self.options.get_safe("fPIC", False) or self.options.shared else ""
        ccopt = f"-Wall -Wextra {optimization} -I."
        shared = "1" if self.options.shared else "0"

        command = " ".join([
            "make",
            "-C", shlex.quote(self.build_folder),
            "-f", "Makefile",
            shlex.quote(f"CC={cc}"),
            shlex.quote(f"CCOPT={ccopt}"),
            shlex.quote(f"CCSHRD={pic}"),
            shlex.quote(f"SHARED={shared}"),
            "all",
        ])
        self.run(command, env="conanbuild")

    def package(self):
        copy(
            self,
            "shhopt.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "README",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        if self.options.shared:
            library = "libshhopt.so.1.1.7"
            copy(
                self,
                library,
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "lib"),
            )
            shutil.copy2(
                os.path.join(self.package_folder, "lib", library),
                os.path.join(self.package_folder, "lib", "libshhopt.so.1"),
            )
            shutil.copy2(
                os.path.join(self.package_folder, "lib", library),
                os.path.join(self.package_folder, "lib", "libshhopt.so"),
            )
        else:
            copy(
                self,
                "libshhopt.a",
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "lib"),
            )

    def package_info(self):
        self.cpp_info.libs = ["shhopt"]
        self.cpp_info.set_property("cmake_file_name", "shhopt")
        self.cpp_info.set_property("cmake_target_name", "shhopt::shhopt")
        self.cpp_info.set_property("pkg_config_name", "shhopt")
        if self.options.shared:
            self.runenv_info.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
            )
