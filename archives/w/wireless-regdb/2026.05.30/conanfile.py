#!/usr/bin/env python3
"""Conan recipe for the wireless regulatory database."""

import os
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class WirelessRegdbConan(ConanFile):
    name = "wireless-regdb"
    version = "2026.05.30"
    description = "Wireless regulatory database maintained by the Linux community"
    license = "ISC"
    homepage = (
        "https://wireless.wiki.kernel.org/en/developers/regulatory/"
        "wireless-regdb"
    )
    url = "https://git.kernel.org/pub/scm/linux/kernel/git/wens/wireless-regdb.git"
    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        copy(
            self,
            "test_wireless_regdb.py",
            src=os.path.join(self.recipe_folder, "test_package"),
            dst=os.path.join(self.export_sources_folder, "test_package"),
        )

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="wireless-regdb-2026.05.30.tar.xz",
            strip_root=True,
        )
        apply_conandata_patches(self)

    @property
    def _validator(self):
        return os.path.join(
            self.export_sources_folder,
            "test_package",
            "test_wireless_regdb.py",
        )

    def build(self):
        command = (
            f'"{sys.executable}" "{self._validator}" '
            f'--source-root "{self.source_folder}"'
        )
        self.run(command)

    def package(self):
        data_dir = os.path.join(self.package_folder, "share", "wireless-regdb")
        tools_dir = os.path.join(data_dir, "tools")
        docs_dir = os.path.join(
            self.package_folder,
            "share",
            "doc",
            "wireless-regdb",
        )

        for filename in ("db.txt", "regulatory.db", "regulatory.db.p7s"):
            copy(
                self,
                filename,
                src=self.source_folder,
                dst=data_dir,
                keep_path=False,
            )
        for filename in ("dbparse.py", "db2fw.py"):
            copy(
                self,
                filename,
                src=self.source_folder,
                dst=tools_dir,
                keep_path=False,
            )
        copy(
            self,
            "README",
            src=self.source_folder,
            dst=docs_dir,
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        data_dir = os.path.join(self.package_folder, "share", "wireless-regdb")
        database = os.path.join(data_dir, "regulatory.db")

        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share"]
        self.buildenv_info.define_path("WIRELESS_REGDB_DIR", data_dir)
        self.buildenv_info.define_path("WIRELESS_REGDB", database)
        self.runenv_info.define_path("WIRELESS_REGDB_DIR", data_dir)
        self.runenv_info.define_path("WIRELESS_REGDB", database)
