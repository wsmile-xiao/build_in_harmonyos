#!/usr/bin/env python3
"""Conan recipe for byobu 6.13 — pure shell/Python script tool (no compilation)."""
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches

_EXCLUDES = ("*.in", "*.am", "Makefile*")

class ByobuConan(ConanFile):
    name = "byobu"
    version = "6.13"
    description = "GNU Screen enhancement - text-based window manager and terminal multiplexer"
    license = "GPL-3.0"
    homepage = "https://github.com/dustinkirkland/byobu"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        prefix = self.package_folder.replace("\\", "/")
        src = Path(self.source_folder)
        for in_file in src.rglob("*.in"):
            if "debian" in str(in_file):
                continue
            content = in_file.read_text(encoding="utf-8")
            content = content.replace("@prefix@", prefix)
            out_file = in_file.with_suffix("")
            out_file.write_text(content, encoding="utf-8")
            out_file.chmod(in_file.stat().st_mode)

    def package(self):
        src = Path(self.source_folder)
        pkg = Path(self.package_folder)
        copy(self, "*", os.path.join(src, "usr", "bin"), os.path.join(pkg, "bin"), excludes=_EXCLUDES)
        bin_dir = os.path.join(pkg, "bin")
        for link_name in ("byobu-screen", "byobu-tmux"):
            link_path = os.path.join(bin_dir, link_name)
            if os.path.exists(link_path):
                os.remove(link_path)
            os.symlink("byobu", link_path)
        copy(self, "*", os.path.join(src, "usr", "lib", "byobu"), os.path.join(pkg, "lib", "byobu"), excludes=_EXCLUDES)
        copy(self, "*", os.path.join(src, "usr", "share", "byobu"), os.path.join(pkg, "share", "byobu"), excludes=_EXCLUDES)
        copy(self, "*", os.path.join(src, "usr", "share", "man", "man1"), os.path.join(pkg, "share", "man", "man1"), excludes=_EXCLUDES)
        copy(self, "*", os.path.join(src, "usr", "share", "doc", "byobu"), os.path.join(pkg, "share", "doc", "byobu"), excludes=_EXCLUDES)
        copy(self, "*", os.path.join(src, "usr", "share", "sounds"), os.path.join(pkg, "share", "sounds"))
        copy(self, "*", os.path.join(src, "usr", "share", "dbus-1", "services"), os.path.join(pkg, "share", "dbus-1", "services"), excludes=_EXCLUDES)
        copy(self, "*", os.path.join(src, "etc"), os.path.join(pkg, "etc"), excludes=_EXCLUDES)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.resdirs = ["share", "etc"]
        self.runenv_info.define("BYOBU_PREFIX", self.package_folder)
