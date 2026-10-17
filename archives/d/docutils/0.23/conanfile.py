import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class DocutilsConan(ConanFile):
    """docutils 0.23 — Python Documentation Utilities (pure Python package).

    Product: lib/python3.12/site-packages/docutils/ + bin/ entry-point scripts.
    Pure Python (no C extensions), flit build backend, no cross-compilation needed.
    Runtime dependency: Python >= 3.9 (provided by target OHOS Python environment).
    """
    name = "docutils"
    version = "0.23"
    description = "Docutils -- Python Documentation Utilities"
    license = "Public Domain, BSD-2-Clause, GPL-3.0"
    homepage = "https://docutils.sourceforge.io"
    url = "https://docutils.sourceforge.io"
    topics = ("documentation", "restructuredtext", "rst", "html", "latex")
    # Pure Python package: only os/arch for platform identification
    settings = "os", "arch"

    # Entry points from pyproject.toml [project.scripts]
    _ENTRY_POINTS = {
        "docutils": "docutils.__main__:main",
        "rst2html": "docutils.core:rst2html",
        "rst2html4": "docutils.core:rst2html4",
        "rst2html5": "docutils.core:rst2html5",
        "rst2latex": "docutils.core:rst2latex",
        "rst2man": "docutils.core:rst2man",
        "rst2odt": "docutils.core:rst2odt",
        "rst2pseudoxml": "docutils.core:rst2pseudoxml",
        "rst2s5": "docutils.core:rst2s5",
        "rst2xetex": "docutils.core:rst2xetex",
        "rst2xml": "docutils.core:rst2xml",
    }

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, strip_root=True, **self.conan_data["sources"])
        apply_conandata_patches(self)

    def build(self):
        # Pure Python package, no compilation step
        pass

    def package(self):
        # Copy docutils/ package to site-packages
        dst_sp = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        os.makedirs(dst_sp, exist_ok=True)
        src_pkg = os.path.join(self.source_folder, "docutils")
        if not os.path.isdir(src_pkg):
            raise Exception("Source package directory not found: " + src_pkg)
        shutil.copytree(src_pkg, os.path.join(dst_sp, "docutils"), dirs_exist_ok=True)

        # Generate entry-point scripts to bin/
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        site_packages_rel = os.path.join("lib", "python3.12", "site-packages")
        for script_name, entry_point in self._ENTRY_POINTS.items():
            module_path, func_name = entry_point.split(":")
            script_content = (
                "#!/usr/bin/env python3\n"
                "import os, sys\n"
                "_pkg_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))\n"
                "_sp = os.path.join(_pkg_root, \"{}\")\n".format(site_packages_rel) +
                "if _sp not in sys.path:\n"
                "    sys.path.insert(0, _sp)\n"
                "from {} import {}\n".format(module_path, func_name) +
                "if __name__ == \"__main__\":\n"
                "    sys.argv[0] = sys.argv[0].removesuffix(\".exe\")\n"
                "    sys.exit({}())\n".format(func_name)
            )
            script_path = os.path.join(bin_dir, script_name)
            with open(script_path, "w") as f:
                f.write(script_content)
            os.chmod(script_path, 0o755)

    def package_info(self):
        # Pure Python package: no C libs/headers, only site-packages resources + bin scripts
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["lib/python3.12/site-packages"]
