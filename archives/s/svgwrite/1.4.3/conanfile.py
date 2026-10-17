#!/usr/bin/env python3
"""Conan recipe candidate for the pure Python svgwrite 1.4.3 library."""

import os
from pathlib import Path
import shlex
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class SvgwriteConan(ConanFile):
    name = "svgwrite"
    version = "1.4.3"
    description = "Python library to create SVG drawings"
    license = "MIT"
    homepage = "https://github.com/mozman/svgwrite"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            extract_filter="data")
        # The fixed upstream sdist uses CRLF in these files. The official
        # refresh-patch output uses LF context, so match that input first.
        for relative in ("svgwrite/data/svgparser.py",
                         "tests/test_pathdataparser.py", "tests/test_style.py"):
            path = Path(self.source_folder) / relative
            original = path.read_bytes()
            path.write_bytes(original.replace(b"\r\n", b"\n"))
        apply_conandata_patches(self)

    def build(self):
        command = [sys.executable, "-m", "compileall", "-q", "-f",
                   "svgwrite", "tests"]
        quoted = (subprocess.list2cmdline(command) if os.name == "nt"
                  else shlex.join(command))
        self.run(quoted, cwd=self.source_folder)

    def package(self):
        source = os.path.join(self.source_folder, "svgwrite")
        target = os.path.join(self.package_folder, "lib", "python", "svgwrite")
        copied = copy(self, "*.py", src=source, dst=target, keep_path=True)
        if not copied:
            raise ConanException("svgwrite Python sources were not packaged")
        for name in ("__init__.py", os.path.join("data", "__init__.py"),
                     os.path.join("extensions", "__init__.py")):
            if not os.path.isfile(os.path.join(target, name)):
                raise ConanException(f"svgwrite package is incomplete: {name}")
        licenses = copy(self, "LICENSE.TXT", src=self.source_folder,
                        dst=os.path.join(self.package_folder, "licenses"),
                        keep_path=False)
        if not licenses:
            raise ConanException("svgwrite LICENSE.TXT was not packaged")

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "lib", "python"))
