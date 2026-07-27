#!/usr/bin/env python3
"""Conan recipe for git-crypt 0.8.0 — Transparent file encryption in git.

git-crypt is a command-line tool that enables transparent encryption of
sensitive files in a git repository. It uses OpenSSL (libcrypto) for
encryption and requires git at runtime.

Build system: simple Makefile (no configure).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GitCryptConan(ConanFile):
    name = "git-crypt"
    version = "0.8.0"
    description = "Transparent file encryption tool for git repositories"
    license = "GPL-3.0"
    homepage = "https://www.agwa.name/projects/git-crypt/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # git-crypt is a CLI tool, not a library
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R32: settings.os must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"git-crypt only supports Linux/OHOS, got {self.settings.os}"
            )
        env = VirtualBuildEnv(self)
        env.generate()

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, not from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")

        # Get OpenSSL include/lib from Conan dependency
        openssl_pkg = self.dependencies["openssl"].package_folder
        openssl_inc = os.path.join(openssl_pkg, "include")
        openssl_lib = os.path.join(openssl_pkg, "lib")

        self.run(
            f'make CXX="{cxx}" '
            f'CXXFLAGS="-Wall -pedantic -Wno-long-long -O2 -std=c++11 -I{openssl_inc}" '
            f'LDFLAGS="-L{openssl_lib} -lcrypto" '
            f'ENABLE_MAN=no -j1',
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package(self):
        # Copy the built binary to package/bin/
        copy(self, "git-crypt", src=os.path.join(self.source_folder),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # git-crypt is a CLI tool — binary in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
