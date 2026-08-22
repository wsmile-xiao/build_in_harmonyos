#!/usr/bin/env python3
"""Conan recipe for rhash 1.4.6 — hash computation tool and library.

Build system: Makefile + configure script.
Produces: librhash.a (static library), rhash (CLI binary).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    chdir,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class RhashConan(ConanFile):
    name = "rhash"
    version = "1.4.6"
    description = "Recursive hash utility and portable library for computing digests"
    license = "0BSD"
    homepage = "https://github.com/rhash/RHash"
    url = ""

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")
        if self.options.shared:
            raise ConanInvalidConfiguration('RHash is packaged as a static library only')

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        config_shell = os.environ.get("CONFIG_SHELL")
        if not config_shell:
            config_shell = "/data/service/hnp/bin/bash" if self.settings.os == "OHOS" else "sh"
        build_tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(build_tmp, exist_ok=True)

        # OpenSSL only accelerates hashes that RHash also implements internally.
        # Disable worker autodetection to keep this static package dependency-free.
        configure_args = " ".join((
            "--prefix=/", f"--cc={cc}", f"--ar={ar}",
            "--enable-static", "--disable-lib-shared",
            "--disable-gettext", "--disable-openssl", "--disable-symlinks",
        ))
        with chdir(self, self.source_folder):
            self.run(f"TMPDIR={build_tmp} CONFIG_SHELL={config_shell} "
                     f"{config_shell} ./configure {configure_args}")
            self.run("make -j1")
            self.run("make -j1 test test-lib")

    def package(self):
        # Copy public headers
        copy(self, "rhash.h", os.path.join(self.source_folder, "librhash"),
             os.path.join(self.package_folder, "include"))
        copy(self, "rhash_torrent.h", os.path.join(self.source_folder, "librhash"),
             os.path.join(self.package_folder, "include"))

        # Copy static library
        copy(self, "librhash.a", os.path.join(self.source_folder, "librhash"),
             os.path.join(self.package_folder, "lib"))

        # Copy rhash binary
        copy(self, "rhash", self.source_folder,
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["rhash"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "rhash")
        self.cpp_info.set_property("cmake_target_name", "rhash::rhash")
