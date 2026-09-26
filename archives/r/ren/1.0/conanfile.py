#!/usr/bin/env python3
"""Conan recipe — ren 1.0 (plain Makefile)."""
import os
import shlex
import urllib.request

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    copy,
    export_conandata_patches,
    get,
    unzip,
)
from conan.tools.layout import basic_layout


class RenConan(ConanFile):
    name = "ren"
    version = "1.0"
    description = "Rename multiple files in a directory using wildcard search and replacement patterns"
    license = "LicenseRef-comp.sources.unix"
    homepage = "https://www.ibiblio.org/pub/Linux/utils/file/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # Pure C tool: C++ settings do not affect the binary.
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ren supports Linux/OHOS only, got {self.settings.os}"
            )

    def source(self):
        data = self.conan_data["sources"][self.version]
        try:
            get(self, **data, strip_root=True)
            return
        except ConanException as exc:
            # ibiblio serves the .tar.gz with Content-Encoding: gzip/x-gzip, so
            # the requests-based downloader stores the decoded tar stream and
            # the sha256 of the official archive cannot match. urllib does not
            # decode Content-Encoding: fetch the raw archive bytes and verify.
            self.output.warning(
                f"conan download failed ({exc}); retrying without "
                "Content-Encoding decoding"
            )
        archive = os.path.join(self.source_folder, f"ren-{self.version}.tar.gz")
        with urllib.request.urlopen(data["url"], timeout=120) as response:
            payload = response.read()
        with open(archive, "wb") as handle:
            handle.write(payload)
        check_sha256(self, archive, data["sha256"])
        unzip(self, archive, destination=self.source_folder, strip_root=True)
        os.remove(archive)

    def build(self):
        apply_conandata_patches(self)
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", check_type=dict, default={}
        )
        cc = compiler_executables.get("c", "cc")
        # ren.c is 1988 K&R C (implicit int, old-style definitions), so it is
        # compiled as gnu89. The upstream Makefile compiles and links in one
        # step with $(CC) $(CFLAGS); the libc-only tool is linked as a static
        # PIE so the packaged binary needs no dynamic loader.
        cflags = "-std=gnu89 -O2 -fPIE -static-pie"
        self.run(
            f"make -j1 CC={shlex.quote(cc)} CFLAGS={shlex.quote(cflags)}",
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        copy(
            self,
            "ren",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "ren.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "README",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "ren"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
