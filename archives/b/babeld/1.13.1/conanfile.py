#!/usr/bin/env python3
"""Conan recipe for babeld 1.13.1 — Babel routing protocol daemon.

babeld uses a plain Makefile (no configure script) and git submodules
(BLAKE2, rfc6234) that are NOT included in GitHub's source archive.
The source() method downloads the main archive plus submodule content.

Submodule sources:
  - BLAKE2: https://github.com/BLAKE2/BLAKE2 (still available)
  - rfc6234: original repo (massar/rfc6234) was deleted;
    using fork https://github.com/bitpart-xyz/rfc6234 (reference/ dir)
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class BabeldConan(ConanFile):
    name = "babeld"
    version = "1.13.1"
    description = "Babel routing protocol daemon"
    license = "MIT"
    homepage = "https://github.com/jech/babeld"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # 1. Download the main source archive from GitHub
        #    GitHub source archives do NOT include git submodule content
        get(self, **self.conan_data["sources"], strip_root=True)

        # 2. Download BLAKE2 submodule (needed for BLAKE2/ref/blake2s-ref.c)
        get(self, "https://github.com/BLAKE2/BLAKE2/archive/refs/heads/master.tar.gz",
            strip_root=True, destination="BLAKE2")

        # 3. Download rfc6234 submodule (needed for rfc6234/sha224-256.c)
        #    Original repo (massar/rfc6234) was deleted from GitHub.
        #    Using fork: bitpart-xyz/rfc6234 — files are in reference/ subdir
        get(self, "https://github.com/bitpart-xyz/rfc6234/archive/refs/heads/main.tar.gz",
            strip_root=True, destination="rfc6234_tmp")
        # Move files from reference/ to rfc6234/ (where babeld Makefile expects them)
        os.makedirs("rfc6234", exist_ok=True)
        ref_dir = os.path.join("rfc6234_tmp", "reference")
        if os.path.isdir(ref_dir):
            for f in os.listdir(ref_dir):
                src_path = os.path.join(ref_dir, f)
                if os.path.isfile(src_path):
                    shutil.copy(src_path, os.path.join("rfc6234", f))
        shutil.rmtree("rfc6234_tmp", ignore_errors=True)

    def generate(self):
        # Use AutotoolsToolchain to generate build environment (CC, CXX, LDFLAGS, etc.)
        # babeld's Makefile does not use configure, but respects CC and LDFLAGS
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        # R32: Platform compatibility check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )
        apply_conandata_patches(self)
        # Fix version: tarball source has no git history, write version.h directly
        version_h = os.path.join(self.source_folder, "version.h")
        with open(version_h, "w") as vf:
            vf.write('#define BABELD_VERSION "babeld-' + self.version + '"\n')
        # babeld uses a plain Makefile (no configure script)
        # R33: CC, CFLAGS, LDFLAGS come from Conan toolchain (conanbuildenv)
        # Run in source_folder where the Makefile is located
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # TARGET acts as DESTDIR in babeld's Makefile
        # PREFIX determines the install layout within TARGET
        self.run(
            f'make install TARGET="{self.package_folder}" PREFIX="/usr/local"',
            cwd=self.source_folder, env="conanbuild"
        )

    def package_info(self):
        # babeld is a standalone binary, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["usr/local/bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
