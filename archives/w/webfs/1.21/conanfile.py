#!/usr/bin/env python3
"""Conan recipe for webfs 1.21 (GNU make)."""

import os
import shutil

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain


class WebfsConan(ConanFile):
    name = "webfs"
    version = "1.21"
    description = "Lightweight static HTTP and HTTPS file server"
    license = "GPL-2.0-only"
    homepage = "https://linux.bytesex.org/misc/webfs.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("http", "https", "static-file-server", "network")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/4.0.1")

    def layout(self):
        # GNUmakefile's config probe writes Make.config in the source directory.
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "conan_generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        openssl = self.dependencies["openssl"]
        tc = AutotoolsToolchain(self)
        for directory in openssl.cpp_info.includedirs:
            tc.extra_cflags.append("-I" + os.path.join(openssl.package_folder, directory))
        for directory in openssl.cpp_info.libdirs:
            tc.extra_ldflags.append("-L" + os.path.join(openssl.package_folder, directory))

        # HarmonyOS can run as an unprivileged numeric UID/GID without passwd/group
        # database entries. The opt-in capability leaves all other builds unchanged.
        if str(self.settings.os) == "OHOS":
            tc.extra_cflags.append("-DWEBFS_MISSING_PASSWD_DB")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HarmonyOS also defines __linux__, so force the portable buffered fallback.
        # The upstream Makefile is plain GNU make, so explicitly load Conan's
        # generated toolchain/build environment (CFLAGS, LDFLAGS, compiler, PATH).
        self.run("make USE_SSL=yes USE_SENDFILE=no -j1", env="conanbuild")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        license_dir = os.path.join(self.package_folder, "licenses")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(man_dir, exist_ok=True)
        os.makedirs(license_dir, exist_ok=True)
        copy(self, "webfsd", src=self.source_folder, dst=bin_dir, keep_path=False)
        shutil.copyfile(os.path.join(self.source_folder, "webfsd.man"),
                        os.path.join(man_dir, "webfsd.1"))
        copy(self, "COPYING", src=self.source_folder, dst=license_dir, keep_path=False)

    def package_info(self):
        # This recipe packages a command-line application, not a linkable library.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
