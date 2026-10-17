#!/usr/bin/env python3
"""Conan recipe for distro 1.9.0 — pure Python OS platform information API.

distro is a pure Python package (no C/C++ compilation).
Product: lib/python3.12/site-packages/distro/ + bin/distro CLI entry.
No third-party Python dependencies (requires_dist=None on PyPI).
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class DistroConan(ConanFile):
    name = "distro"
    version = "1.9.0"
    package_type = "application"
    license = "Apache-2.0"
    homepage = "https://github.com/python-distro/distro"
    description = (
        "Distro - an OS platform information API (pure Python, "
        "replacement for platform.linux_distribution)"
    )
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # 纯 Python 包无编译步骤，先验证源码布局和语法。
        src = os.path.join(self.source_folder, "src", "distro")
        init_py = os.path.join(src, "__init__.py")
        if not os.path.isfile(init_py):
            raise ConanException(f"distro 源码缺失: {init_py}")
        self.run(f"python3 -m py_compile {init_py}")

    def package(self):
        src = os.path.join(self.source_folder, "src", "distro")
        dst = os.path.join(self.package_folder, "lib", "python3.12", "site-packages", "distro")
        shutil.copytree(src, dst)

        # Generate bin/distro CLI entry point
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        entry = os.path.join(bindir, "distro")
        with open(entry, "w") as f:
            f.write("#!/usr/bin/env python3\n")
            f.write("import os, sys\n")
            f.write(f"sys.path.insert(0, os.path.join('{self.package_folder}', 'lib', 'python3.12', 'site-packages'))\n")
            f.write("from distro.distro import main\n")
            f.write("main()\n")
        os.chmod(entry, 0o755)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.append_path(
            "PYTHONPATH",
            os.path.join(self.package_folder, "lib", "python3.12", "site-packages"),
        )
