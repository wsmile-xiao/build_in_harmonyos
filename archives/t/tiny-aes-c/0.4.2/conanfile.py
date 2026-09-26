#!/usr/bin/env python3
"""Conan recipe for CryptoManiac/tiny-aes-cpp 0.4.2.

The upstream snapshot is intentionally tiny and does not ship a build system.
This recipe builds its single implementation file into a static archive.
"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class TinyAesCppConan(ConanFile):
    name = "tiny-aes-c"
    version = "0.4.2"
    description = "Dependency-free C++ AES-256-CTR library"
    license = "Unlicense"
    homepage = "https://github.com/CryptoManiac/tiny-aes-cpp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("aes", "crypto", "ctr", "encryption", "cxx")
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_executables(self):
        return (
            self.conf.get(
                "tools.build:compiler_executables",
                default={},
                check_type=dict,
            )
            or {}
        )

    def _cxx(self):
        cxx = self._compiler_executables().get("cpp")
        if not cxx:
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables must define the C++ compiler as 'cpp'"
            )
        return cxx

    def _ar(self, cxx):
        configured = self._compiler_executables().get("ar")
        if configured:
            return configured
        compiler_dir = os.path.dirname(cxx)
        for candidate in ("llvm-ar", "llvm-ar.exe"):
            path = os.path.join(compiler_dir, candidate)
            if compiler_dir and os.path.isfile(path):
                return path
        raise ConanInvalidConfiguration(
            "tools.build:compiler_executables must define 'ar', or llvm-ar "
            "must be next to the configured C++ compiler"
        )

    def build(self):
        apply_conandata_patches(self)

        cxx = self._cxx()
        ar = self._ar(cxx)
        source = os.path.join(self.source_folder, "aes.cpp")
        object_file = os.path.join(self.build_folder, "aes.o")
        archive = os.path.join(self.build_folder, "libtiny-aes-c.a")
        os.makedirs(self.build_folder, exist_ok=True)

        flags = [
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
            "-Werror",
            # The OHOS clang wrapper injects linker-only flags into compile
            # commands; keep source warnings fatal without rejecting those.
            "-Wno-error=unused-command-line-argument",
        ]
        if self.options.get_safe("fPIC"):
            flags.append("-fPIC")
        self.run(
            "{cxx} {flags} -I{include} -c {source} -o {object}".format(
                cxx=shlex.quote(cxx),
                flags=" ".join(flags),
                include=shlex.quote(self.source_folder),
                source=shlex.quote(source),
                object=shlex.quote(object_file),
            ),
            cwd=self.source_folder,
        )
        self.run(
            "{ar} rcs {archive} {object}".format(
                ar=shlex.quote(ar),
                archive=shlex.quote(archive),
                object=shlex.quote(object_file),
            ),
            cwd=self.build_folder,
        )

    def package(self):
        copy(
            self,
            "aes.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libtiny-aes-c.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "unlicense.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["tiny-aes-c"]
        self.cpp_info.set_property("cmake_file_name", "tiny-aes-c")
        self.cpp_info.set_property("cmake_target_name", "tiny-aes-c::tiny-aes-c")
        self.cpp_info.set_property("pkg_config_name", "tiny-aes-c")
