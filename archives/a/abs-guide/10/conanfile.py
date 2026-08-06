#!/usr/bin/env python3
"""Conan recipe — abs-guide 10 (pure HTML documentation package).

The Advanced Bash-Scripting Guide (v10, 2014-03-10) by Mendel Cooper.
Pure documentation package: 140 pre-rendered HTML pages, no source code
and no build system. The recipe only downloads the tarball and installs
the HTML pages into the package (share/doc/abs-guide/).
"""

from conan import ConanFile
from conan.tools.files import copy, get, export_conandata_patches, apply_conandata_patches
import os


class AbsGuideConan(ConanFile):
    name = "abs-guide"
    version = "10"
    description = "The Advanced Bash-Scripting Guide — HTML documentation (v10)"
    license = "Public-Domain"
    homepage = "https://tldp.org/LDP/abs/html/"

    package_type = "application"

    settings = "os", "arch"

    def requirements(self):
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # Fossies 镜像拒绝浏览器类 UA（HTTP 401），需使用 curl/wget 类 UA
        get(self, **self.conan_data["sources"], strip_root=True,
            headers={"User-Agent": "curl/8.5.0"})

    def build(self):
        apply_conandata_patches(self)
        # Pure documentation package: HTML pages are pre-rendered upstream,
        # no compilation is needed.
        pass

    def package(self):
        """Install the HTML pages to share/doc/abs-guide/."""
        doc_dir = os.path.join(self.package_folder, "share", "doc", "abs-guide")
        copy(self, "*.html", self.source_folder, doc_dir, keep_path=False)

    def package_info(self):
        # Documentation package — no cpp_info needed
        pass
