#!/usr/bin/env python3
"""Conan recipe for TapTempo 1.4.5 (CMake)."""

import hashlib
import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    copy,
    export_conandata_patches,
    get,
    unzip,
)


class TaptempoConan(ConanFile):
    name = "taptempo"
    version = "1.4.5"
    description = "Command-line tap tempo and BPM calculator"
    license = "GPL-3.0-or-later"
    homepage = "https://taptempo.tuxfamily.org/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"with_nls": [True, False]}
    default_options = {"with_nls": False}

    def configure(self):
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("TapTempo is supported on Linux and OHOS")
        if str(self.settings.compiler) not in ("gcc", "clang"):
            raise ConanInvalidConfiguration("TapTempo needs GCC or Clang with C++11")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        local_archive = os.environ.get("TAPTEMPO_SOURCE_ARCHIVE")
        if local_archive:
            # H1 can use the identical, hash-checked archive without network access.
            check_sha256(self, local_archive, source["sha256"])
            unzip(self, local_archive, destination=self.source_folder,
                  strip_root=True, extract_filter="data")
        else:
            get(self, **source, strip_root=True, extract_filter="data")

        # The official per-file patch generator uses LF context for this CRLF file.
        main_cpp = Path(self.source_folder) / "src" / "main.cpp"
        contents = main_cpp.read_bytes()
        digest = hashlib.sha256(contents).hexdigest()
        original = "54725341d4397c0a61ad7963eabcb9a4cf5ffe94765df2c8b308bb2959352aae"
        normalized = "f83c0b1ff082c024ce13a675198b2d007368c79c8e6c9151d87c058f54e78cf3"
        if digest == original:
            contents = contents.replace(b"\r\n", b"\n")
            if hashlib.sha256(contents).hexdigest() != normalized:
                raise ConanException("Unexpected TapTempo main.cpp line endings")
            main_cpp.write_bytes(contents)
        elif digest != normalized:
            raise ConanException("Unexpected TapTempo main.cpp source hash")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["TAPTEMPO_ENABLE_NLS"] = bool(self.options.with_nls)
        tc.variables["TAPTEMPO_BUILD_TESTS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
