#!/usr/bin/env python3
"""Conan recipe — runit 2.3.1 (makefile)."""
from pathlib import Path

from conan import ConanFile
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout


class RunitConan(ConanFile):
    name = "runit"
    version = "2.3.1"
    description = "A UNIX init scheme with service supervision."
    license = "BSD-3-Clause"
    homepage = "https://smarden.org/runit/"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        source_folder = Path(self.source_folder)
        for candidate in (
            source_folder / "src",
            source_folder / "runit-2.3.1" / "src",
            source_folder / "admin" / "runit-2.3.1" / "src",
        ):
            if candidate.is_dir():
                for item in candidate.iterdir():
                    item.rename(source_folder / item.name)
                break

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        cflags = "-O2 -fPIC"
        ldflags = "-s"
        if self.settings.build_type == "Debug":
            cflags = "-g -fPIC"
            ldflags = ""
        save(self, "conf-cc", f"{cc} {cflags}\n")
        save(self, "conf-ld", f"{cc} {ldflags}\n".strip() + "\n")
        save(self, "conf-ar", f"{ar} cr\n")
        self.run("make -j1")

    def package(self):
        bin_dir = Path(self.package_folder) / "bin"
        for program in [
            "chpst",
            "runit",
            "runit-init",
            "runsv",
            "runsvchdir",
            "runsvdir",
            "sv",
            "svlogd",
            "utmpset",
        ]:
            copied = copy(self, program, src=self.build_folder, dst=bin_dir)
            if not copied:
                raise RuntimeError(f"missing built executable: {program}")
        man_dir = Path(self.source_folder) / "man"
        if not man_dir.is_dir():
            man_dir = Path(self.source_folder) / "runit-2.3.1" / "man"
        man_copied = copy(
            self,
            "*.8",
            src=man_dir,
            dst=Path(self.package_folder) / "share" / "man" / "man8",
        )
        if not man_copied:
            raise RuntimeError(f"missing runit man pages: {man_dir}")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
