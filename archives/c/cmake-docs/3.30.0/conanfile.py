#!/usr/bin/env python3
"""Conan recipe — cmake-docs 3.30.0 (Sphinx HTML documentation)."""
import os
import re
import sys

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class CmakeDocsConan(ConanFile):
    name = "cmake-docs"
    version = "3.30.0"
    description = "CMake official HTML documentation (offline)"
    license = "BSD-3-Clause"
    homepage = "https://cmake.org/documentation/"

    package_type = "build-scripts"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Create conf.py from conf.py.in (bypass CMake to avoid find_program issues)
        sphinx_src = os.path.join(self.source_folder, "Utilities", "Sphinx")
        conf_in = os.path.join(sphinx_src, "conf.py.in")

        with open(conf_in, "r") as f:
            content = f.read()

        # Read copyright from Copyright.txt
        copyright_path = os.path.join(self.source_folder, "Copyright.txt")
        conf_copyright = "Kitware, Inc."
        with open(copyright_path, "r") as f:
            for line in f:
                m = re.match(r'^Copyright (2000-20[0-9][0-9] Kitware.*)', line)
                if m:
                    conf_copyright = m.group(1)
                    break

        # Replace template variables
        content = content.replace("@conf_path@", sphinx_src)
        content = content.replace("@conf_docs@", os.path.join(self.source_folder, "Help"))
        content = content.replace("@conf_version@", "3.30.0")
        content = content.replace("@conf_release@", "3.30.0")
        content = content.replace("@conf_copyright@", conf_copyright)
        content = content.replace("@conf_baseurl@", "")

        # Write conf.py to build directory
        build_dir = self.build_folder
        os.makedirs(build_dir, exist_ok=True)
        with open(os.path.join(build_dir, "conf.py"), "w") as f:
            f.write(content)

    def build(self):
        apply_conandata_patches(self)
        # Use the same Python that runs Conan to install and invoke Sphinx.
        # This avoids PATH issues where sphinx-build is not found.
        py = sys.executable
        self.run(f'{py} -m pip install "sphinx>=9.1.0" "sphinx-rtd-theme>=3.1.0"')
        help_dir = os.path.join(self.source_folder, "Help")
        build_dir = self.build_folder
        html_dir = os.path.join(build_dir, "html")
        doctree_dir = os.path.join(build_dir, "doctrees")
        # Use python -m sphinx (equivalent to sphinx-build but doesn't need PATH)
        self.run(
            f'{py} -m sphinx -c "{build_dir}" -d "{doctree_dir}" '
            f'-b html "{help_dir}" "{html_dir}"'
        )

    def package(self):
        html_dir = os.path.join(self.build_folder, "html")
        copy(self, "*", src=html_dir,
             dst=os.path.join(self.package_folder, "doc", "cmake-3.30", "html"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["doc"]
