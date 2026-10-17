import os
import subprocess
import shutil

from conan import ConanFile
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches,
    check_sha256, unzip
)
from conan.tools.layout import basic_layout


class PhoonConan(ConanFile):
    name = "phoon"
    version = "20140814"
    description = "Display the current moon phase as ASCII art"
    license = "BSD-2-Clause"
    homepage = "https://www.acme.com/software/phoon/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception as e:
            # Fallback for servers with incompatible TLS (acme.com uses
            # AES256-GCM-SHA384 which Python's OpenSSL rejects).
            # Log the original error so it's not silently swallowed.
            self.output.warning(f"Conan get() failed ({e}); falling back to curl")
            url = self.conan_data["sources"]["url"]
            sha256 = self.conan_data["sources"]["sha256"]
            filename = url.rsplit("/", 1)[-1]
            filepath = os.path.join(self.source_folder, filename)
            curl = shutil.which("curl") or "/usr/bin/curl"
            subprocess.run([curl, "-kL", "-o", filepath, url], check=True)
            check_sha256(self, filepath, sha256)
            unzip(self, filepath, self.source_folder, strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        self.run(f"make -C {self.source_folder} CC={cc} -j1")

    def package(self):
        self.run(f"make -C {self.source_folder} install DESTDIR={self.package_folder} PREFIX=")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
