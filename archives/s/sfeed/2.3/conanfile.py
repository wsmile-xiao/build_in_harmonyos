#!/usr/bin/env python3
"""Conan recipe for sfeed 2.3."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class SfeedConan(ConanFile):
    name = "sfeed"
    version = "2.3"
    description = "RSS and Atom feed parser with format conversion tools"
    license = "ISC"
    homepage = "https://codemadness.org/sfeed-simple-feed-parser.html"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sfeed supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, verify=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        make_args = (
            'SFEED_CURSES="" '
            'CC="${CC:-cc}" AR="${AR:-ar}" RANLIB="${RANLIB:-ranlib}"'
        )
        self.run(f"make -j1 {make_args}", cwd=self.source_folder, env="conanbuild")

    def package(self):
        bin_names = [
            "sfeed",
            "sfeed_atom",
            "sfeed_frames",
            "sfeed_gopher",
            "sfeed_html",
            "sfeed_json",
            "sfeed_mbox",
            "sfeed_opml_import",
            "sfeed_plain",
            "sfeed_twtxt",
            "sfeed_web",
            "sfeed_xmlenc",
            "sfeed_content",
            "sfeed_markread",
            "sfeed_opml_export",
            "sfeed_update",
        ]
        docs = ["README", "README.xml", "sfeedrc.example", "style.css"]

        for name in bin_names:
            copy(
                self,
                name,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "bin"),
                keep_path=False,
            )
            path = os.path.join(self.package_folder, "bin", name)
            if os.path.exists(path):
                os.chmod(path, 0o755)

        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(
            self,
            "*.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "*.5",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man5"),
            keep_path=False,
        )
        for pattern in docs:
            copy(
                self,
                pattern,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "share", "doc", "sfeed"),
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
