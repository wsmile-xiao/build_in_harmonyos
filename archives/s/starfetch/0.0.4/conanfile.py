#!/usr/bin/env python3
"""Conan recipe for starfetch 0.0.4 — constellation display CLI tool.

starfetch is a single-file C++17 command line tool that prints a random or
named constellation together with its informational data. nlohmann/json is
vendored as a single header, so the build needs no external library.

The upstream makefile wraps a single compile command and its install target
hardcodes /usr/local, so this recipe compiles the executable directly and
packages resources under share/starfetch. A small patch makes the resource
directory overridable through STARFETCH_RES_DIR so the installed package is
relocatable (required on OHOS where /usr/local/share is not writable).

Upstream ships no test suite; the consumer test in test_package exercises
the installed executable and its data files.
"""

import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class StarfetchConan(ConanFile):
    name = "starfetch"
    version = "0.0.4"
    description = "Command line tool that displays constellations"
    license = "GPL-3.0"
    homepage = "https://github.com/Haruno19/starfetch"
    url = "https://github.com/Haruno19/starfetch"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    _res_subdir = os.path.join("share", "starfetch")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os must check against a set, never == "Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"starfetch only supports Linux/OHOS, got {self.settings.os}"
            )

    def source(self):
        get(
            self,
            **self.conan_data["sources"][self.version],
            filename="starfetch-0.0.4.tar.gz",
            strip_root=True,
        )

    def _cxx(self):
        # R33: compiler executable from Conan conf, never bare shell env vars.
        comps = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return comps.get("cxx") or "clang++"

    def _sign_elf(self, path):
        """Sign the ELF binary so HarmonyOS allows executing it (E077).

        binary-sign-tool only exists on OHOS; on other build hosts this is a
        no-op, leaving CI's release signing step to do the final signing.
        """
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if Path(sign_tool).exists():
            self.run(f"{objcopy} --remove-section .codesign {path} || true")
            self.run(
                f"{sign_tool} sign -inFile {path} -outFile {path}.signed "
                "-selfSign 1"
            )
            shutil.move(f"{path}.signed", path)
        os.chmod(path, 0o755)

    def build(self):
        apply_conandata_patches(self)
        cxx = self._cxx()
        # Equivalent to the upstream `make starfetch` target, minus the
        # install part that hardcodes /usr/local paths.
        self.run(
            f'cd "{self.source_folder}" && '
            f"{cxx} -O2 -Wall -std=c++17 src/starfetch.cpp -o starfetch"
        )
        if self.settings.os == "OHOS":
            self._sign_elf(os.path.join(self.source_folder, "starfetch"))

    def package(self):
        copy(
            self,
            "starfetch",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, self._res_subdir, "doc"),
        )
        copy(
            self,
            "*.json",
            src=os.path.join(self.source_folder, "res", "constellations"),
            dst=os.path.join(
                self.package_folder, self._res_subdir, "constellations"
            ),
        )
        copy(
            self,
            "template",
            src=os.path.join(self.source_folder, "res"),
            dst=os.path.join(self.package_folder, self._res_subdir),
            keep_path=False,
        )
        copy(
            self,
            "help_message.txt",
            src=os.path.join(self.source_folder, "res"),
            dst=os.path.join(self.package_folder, self._res_subdir),
            keep_path=False,
        )

    def package_info(self):
        # CLI application — no public library interface.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        res_dir = os.path.join(self.package_folder, self._res_subdir)
        self.runenv_info.define_path("STARFETCH_RES_DIR", res_dir)
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
