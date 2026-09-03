#!/usr/bin/env python3
"""Conan recipe for py-cpuinfo 9.0.0 — pure Python CPU info library.

py-cpuinfo gets CPU info with pure Python. Provides both a library API
(cpuinfo.get_cpu_info()) and a console script `cpuinfo`. Pure Python,
no C/C++ compilation needed.
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PyCpuinfoConan(ConanFile):
    name = "py-cpuinfo"
    version = "9.0.0"
    description = "Get CPU info with pure Python"
    license = "MIT"
    homepage = "https://github.com/workhorsy/py-cpuinfo"
    url = ""

    # Pure Python noarch: no compiler needed, but OHOS profile requires all 4 settings
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][self.version],
            filename="py-cpuinfo-9.0.0.tar.gz",
            strip_root=True,
        )

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def build(self):
        apply_conandata_patches(self)

        python_exe = sys.executable
        src_dir = self.source_folder
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)

        # Build deps: setuptools + wheel
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 setuptools wheel',
        )

        # Install into staging via --prefix (also places console_scripts in bin/)
        self.run(
            f'{python_exe} -m pip install --break-system-packages --no-deps '
            f'--prefix="{staging}" "{src_dir}"',
        )

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        py_ver = self._py_ver()
        site_dst = os.path.join(
            self.package_folder, "lib", py_ver, "site-packages"
        )
        bin_dst = os.path.join(self.package_folder, "bin")

        site_src = None
        for candidate in (
            os.path.join(staging, "lib", py_ver, "site-packages"),
            os.path.join(staging, "lib", py_ver, "dist-packages"),
            os.path.join(staging, "local", "lib", py_ver, "site-packages"),
            os.path.join(staging, "local", "lib", py_ver, "dist-packages"),
        ):
            if os.path.isdir(candidate) and os.path.isdir(
                os.path.join(candidate, "cpuinfo")
            ):
                site_src = candidate
                break
        if site_src is None:
            raise Exception(
                f"cpuinfo site-packages not found under staging={staging}"
            )

        copy(self, "*", src=site_src, dst=site_dst)

        for bin_src in (
            os.path.join(staging, "bin"),
            os.path.join(staging, "local", "bin"),
        ):
            if os.path.isdir(bin_src):
                copy(self, "*", src=bin_src, dst=bin_dst)

        # pip embeds the build-machine Python path in console-script shebangs.
        # Replace it with a portable wrapper for relocatable Conan packages.
        cli_path = os.path.join(bin_dst, "cpuinfo")
        if os.path.isfile(cli_path):
            with open(cli_path, "w", encoding="utf-8") as cli:
                cli.write("#!/bin/sh\nexec python3 -m cpuinfo \"$@\"\n")
            os.chmod(cli_path, 0o755)

        for lic_name in ("LICENSE", "LICENSE.txt", "LICENSE.md"):
            src = os.path.join(self.source_folder, lic_name)
            if os.path.isfile(src):
                copy(
                    self,
                    lic_name,
                    src=self.source_folder,
                    dst=os.path.join(self.package_folder, "licenses"),
                )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

        site_packages = os.path.join(
            self.package_folder, "lib", self._py_ver(), "site-packages"
        )
        self.runenv_info.append_path("PYTHONPATH", site_packages)
        self.buildenv_info.append_path("PYTHONPATH", site_packages)
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)
