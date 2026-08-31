#!/usr/bin/env python3
"""Conan recipe for cdecode 1.0.0 (libb64 base64 library).

libb64 is a small public-domain base64 encode/decode C library: cdecode.c /
cencode.c build into a single static archive libb64.a through a bare Makefile
rule (`libb64.a: cencode.o cdecode.o`) with no configure step and no third
party dependencies beyond libc.  The consumer test round-trips a byte buffer
through the streaming base64 API to bind the test to the actual archive.
"""

import os
import shutil

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class CdecodeConan(ConanFile):
    name = "cdecode"
    version = "1.0.0"
    description = "Base64 encode/decode C library (libb64)"
    license = "Public-Domain"
    homepage = "https://sourceforge.net/projects/libb64/"
    url = "https://sourceforge.net/projects/libb64/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # Conan 2 requires library packages to declare the shared option.
    # libb64's bare Makefile only produces a static libb64.a.
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = "conandata.yml"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def build(self):
        # Bare Makefile: `libb64.a: cencode.o cdecode.o` with CC/AR.  Use the
        # OHOS clang toolchain explicitly and -j1 to mirror the CI-verified
        # pattern used elsewhere in this repo (workers lack /tmp and have no
        # build uid in /etc/passwd, so parallel make can race on temp files).
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        cc = self._compiler_executable("c", "clang")
        ar = self._compiler_executable("lib", "llvm-ar") or "ar"
        src = os.path.join(self.source_folder, "src")
        with VirtualBuildEnv(self).vars().apply():
            self.run(
                f"make -C {src} CC={cc} AR={ar} -j1 "
                f"TMPDIR={tmpdir} TMP={tmpdir} TEMP={tmpdir}"
            )

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def package(self):
        copy(
            self,
            "libb64.a",
            os.path.join(self.source_folder, "src"),
            os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "*.h",
            os.path.join(self.source_folder, "include", "b64"),
            os.path.join(self.package_folder, "include", "b64"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["b64"]
        self.output.info("cdecode (libb64) static library installed")
