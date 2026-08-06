#!/usr/bin/env python3
"""Test package — cmake-docs 3.30.0 (verify HTML documentation files)."""
import os
import glob

from conan import ConanFile


class CmakeDocsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["cmake-docs"]
        pkg_root = dep.package_folder
        # Find the HTML documentation directory
        html_files = glob.glob(
            os.path.join(pkg_root, "**", "html", "index.html"),
            recursive=True,
        )
        if not html_files:
            raise Exception("CMake HTML documentation (index.html) not found in package")
        doc_dir = os.path.dirname(html_files[0])
        # Verify key documentation files exist
        for f in ["index.html", "searchindex.js", "genindex.html"]:
            path = os.path.join(doc_dir, f)
            if not os.path.isfile(path):
                raise Exception(f"{f} not found in documentation package")
            self.run(f'test -s "{path}"')
