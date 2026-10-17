import os
import hashlib

from conan import ConanFile
from conan.tools.files import copy, unzip, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Mp3ValConan(ConanFile):
    name = "mp3val"
    version = "0.1.8"
    description = "MP3val is a small, high-quality tool for validating and fixing MPEG audio files"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/mp3val/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        url = self.conan_data["sources"]["url"]
        sha256 = self.conan_data["sources"]["sha256"]
        archive = "mp3val-0.1.8-src.tar.gz"
        # SourceForge blocks Python urllib, use curl for download
        self.run(f"curl -L -s -o {archive} '{url}'")
        # Verify sha256
        with open(archive, "rb") as f:
            actual = hashlib.sha256(f.read()).hexdigest()
        if actual != sha256:
            raise Exception(f"SHA256 mismatch: expected {sha256}, got {actual}")
        unzip(self, archive, strip_root=True)
        os.remove(archive)

    def build(self):
        # Source uses CRLF (Windows), convert to LF for patch compatibility
        self.run("sed -i 's/\\r$//' crossapi.cpp", cwd=self.source_folder)
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cxx = compilers.get("cpp", "clang++") if isinstance(compilers, dict) else "clang++"
        # R9: Always use -j1
        self.run(f'make CXX={cxx} CXXFLAGS="-Wall -O2 -fPIC" -j1', cwd=self.source_folder)

    def package(self):
        copy(self, "mp3val", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
