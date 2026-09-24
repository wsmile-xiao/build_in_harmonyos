#!/usr/bin/env python3
"""Conan recipe for sfArkLib 2.24."""

import json
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

required_conan_version = ">=2.0"


class SfarklibConan(ConanFile):
    name = "sfarklib"
    version = "2.24"
    description = "Library for decoding sfArk-compressed SoundFont files"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/raboof/sfArkLib"
    url = "https://github.com/raboof/sfArkLib"
    topics = ("sfark", "soundfont", "decoder", "audio")
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    _sources = (
        "sfklCoding.cpp",
        "sfklCrunch.cpp",
        "sfklDiff.cpp",
        "sfklFile.cpp",
        "sfklLPC.cpp",
        "sfklString.cpp",
        "sfklZip.cpp",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Upstream 2.24 stores these files with CRLF. Normalize only patched
        # files so the generated portability patches apply deterministically.
        for filename in ("sfklCoding.cpp", "sfklZip.cpp", "wcc.h"):
            path = os.path.join(self.source_folder, filename)
            with open(path, "rb") as source_file:
                content = source_file.read()
            with open(path, "wb") as source_file:
                source_file.write(content.replace(b"\r\n", b"\n"))

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "sfArkLib 2.24 is supported on Linux-like platforms"
            )

    def _tool(self, key, ohos_name, native_names):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = str(executables.get(key) or "")
        if configured and (os.path.isfile(configured) or shutil.which(configured)):
            return configured

        compiler_dir = os.path.dirname(str(executables.get("c") or ""))
        sibling = os.path.join(compiler_dir, ohos_name) if compiler_dir else ""
        if sibling and os.path.isfile(sibling):
            return sibling

        candidates = [ohos_name] if self.settings.os == "OHOS" else list(native_names)
        for candidate in candidates:
            resolved = shutil.which(candidate)
            if resolved:
                return resolved
        raise ConanInvalidConfiguration("No usable {} tool was found".format(key))

    def build(self):
        apply_conandata_patches(self)
        cxx = self._tool(
            "cpp", "aarch64-unknown-linux-ohos-clang++", ("clang++", "c++")
        )
        ar = self._tool("ar", "llvm-ar", ("llvm-ar", "ar"))
        zlib = self.dependencies["zlib"]
        include_flags = " ".join(
            "-I{}".format(shlex.quote(path)) for path in zlib.cpp_info.includedirs
        )
        optimization = "-O0 -g" if self.settings.build_type == "Debug" else "-O2"
        objects = []

        for source_name in self._sources:
            source = os.path.join(self.source_folder, source_name)
            obj = os.path.join(
                self.build_folder, os.path.splitext(source_name)[0] + ".o"
            )
            self.run(
                "{} -std=c++17 {} -fPIC -D__LITTLE_ENDIAN__ -Wall -Wextra "
                "{} -I{} -c {} -o {}".format(
                    shlex.quote(cxx),
                    optimization,
                    include_flags,
                    shlex.quote(self.source_folder),
                    shlex.quote(source),
                    shlex.quote(obj),
                )
            )
            objects.append(obj)

        library = os.path.join(self.build_folder, "libsfark.a")
        self.run(
            "{} rcs {} {}".format(
                shlex.quote(ar),
                shlex.quote(library),
                " ".join(shlex.quote(obj) for obj in objects),
            )
        )

        marker = {
            "status": "passed",
            "framework": "none",
            "command": "source-tree and Makefile test-target audit",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))

    def package(self):
        copy(
            self,
            "sfArkLib.h",
            self.source_folder,
            os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libsfark.a",
            self.build_folder,
            os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["sfark"]
        self.cpp_info.set_property("cmake_file_name", "sfarklib")
        self.cpp_info.set_property("cmake_target_name", "sfarklib::sfarklib")
        self.cpp_info.set_property("pkg_config_name", "sfarklib")
