#!/usr/bin/env python3
"""Conan recipe — comgt 0.32 (plain makefile).

comgt is a command-line tool for controlling 3G/GSM modems via AT commands
and its own script language. Build system: plain makefile (no configure).
Upstream has no automated test suite; the package ships the comgt binary.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ComgtConan(ConanFile):
    name = "comgt"
    version = "0.32"
    description = "3G/GSM modem control and scripting tool"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/comgt/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"comgt supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The release tarball stores entries as ./comgt.0.32/..., which Conan's
        # strip_root cannot collapse; flatten the single subdirectory here so
        # patches and the makefile live at the source root.
        sub = os.path.join(self.source_folder, "comgt.0.32")
        if os.path.isdir(sub):
            for item in os.listdir(sub):
                os.rename(os.path.join(sub, item),
                          os.path.join(self.source_folder, item))
            os.rmdir(sub)

    def _src(self):
        # The release tarball stores entries as ./comgt.0.32/..., which Conan's
        # strip_root does not collapse; the makefile lives one level deeper.
        sub = os.path.join(self.source_folder, "comgt.0.32")
        return sub if os.path.isfile(os.path.join(sub, "Makefile")) else self.source_folder

    def build(self):
        apply_conandata_patches(self)
        comp = self.conf.get(
            "tools.build:compiler_executables", check_type=dict, default={}
        )
        cc = comp.get("c", "clang") if comp else "clang"
        src = self._src()
        # The makefile rules hardcode `cc` (not $(CC)); shim a cc -> clang
        # link onto PATH because the OHOS host has no `cc`.
        toolbin = os.path.join(self.build_folder, "_toolbin")
        os.makedirs(toolbin, exist_ok=True)
        link = os.path.join(toolbin, "cc")
        if not os.path.exists(link):
            try:
                os.symlink(shutil.which(cc) or cc, link)
            except OSError:
                shutil.copy2(shutil.which(cc) or cc, link)
        self.run(f'PATH="{toolbin}:$PATH" make -j1', env="conanbuild", cwd=src)

    def package(self):
        src = self._src()
        # The makefile install target hardcodes /usr/local and /etc and runs
        # chmod; copy the built artifacts directly instead.
        copy(self, "comgt", src=src,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "comgt.1", src=src,
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
