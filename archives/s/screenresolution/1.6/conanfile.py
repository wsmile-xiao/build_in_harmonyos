#!/usr/bin/env python3
"""Conan recipe - screenresolution 1.6."""
import os
import glob
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ScreenresolutionConan(ConanFile):
    name = "screenresolution"
    version = "1.6"
    description = "Command line utility for querying display resolution"
    license = "GPL-2.0-only"
    homepage = "https://github.com/jhford/screenresolution"
    url = "https://github.com/jhford/screenresolution"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os == "Linux":
            raise ConanInvalidConfiguration(
                "screenresolution 1.6 has no Linux display backend in this recipe"
            )
        if self.settings.os not in ("Macos", "OHOS"):
            raise ConanInvalidConfiguration(
                f"screenresolution 1.6 supports macOS and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _c_compiler(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        configured = compilers.get("c")
        if not configured:
            raise ConanInvalidConfiguration("tools.build:compiler_executables must define a C compiler")

        candidates = [configured]
        if self.settings.os == "OHOS":
            shadow_clang = os.path.join(os.path.expanduser("~"), "ohpc-ci-shadow", "runs", "*", "tools", "clang")
            candidates.extend(sorted(glob.glob(shadow_clang), key=os.path.getmtime, reverse=True))

        seen = set()
        skipped = []
        for cc in [candidate for candidate in candidates if candidate]:
            if cc in seen:
                continue
            seen.add(cc)
            try:
                subprocess.run(
                    [cc, "--version"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                    timeout=10,
                )
            except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                skipped.append(cc)
                self.output.warning(f"Skipping unusable C compiler: {cc}")
                continue
            if configured and cc != configured:
                self.output.warning(f"Configured C compiler not usable: {configured}; using {cc}")
            return cc

        checked = ", ".join(skipped) if skipped else configured
        raise ConanInvalidConfiguration(f"No usable C compiler found; checked: {checked}")

    def build(self):
        apply_conandata_patches(self)
        self.run("make clean")
        cc = self._c_compiler()
        if self.settings.os == "OHOS":
            self.run(f'make build OHOS=1 CC="{cc}" ARCH_FLAGS=""')
        else:
            self.run(f'make build CC="{cc}"')

    def package(self):
        if self.settings.os == "OHOS":
            copy(self, "screenresolution", self.build_folder, os.path.join(self.package_folder, "bin"))
            bin_path = os.path.join(self.package_folder, "bin", "screenresolution")
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            if os.path.exists(sign_tool) and os.path.exists(objcopy):
                tmp_signed = bin_path + ".signed"
                self.run(f"{objcopy} --remove-section .codesign {bin_path}", quiet=True)
                self.run(
                    f"{sign_tool} sign -inFile {bin_path} -outFile {tmp_signed} -selfSign 1",
                    quiet=True,
                )
                os.replace(tmp_signed, bin_path)
                os.chmod(bin_path, 0o755)
        else:
            self.run(f"make install DESTDIR={self.package_folder} PREFIX=/")
        copy(self, "gpl-2.0.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
