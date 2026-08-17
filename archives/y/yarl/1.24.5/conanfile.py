#!/usr/bin/env python3
"""Conan recipe for yarl 1.24.5 — Python library (setuptools + optional C extension).

HarmonyOS PC adaptation: packages the pure-Python fallback of yarl
(the _quoting_c C extension is optional; yarl degrades to _quoting_py).
Requires idna, multidict, propcache (all published in main).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class YarlConan(ConanFile):
    name = "yarl"
    version = "1.24.5"
    description = "Yet another URL library"
    license = "Apache-2.0"
    homepage = "https://github.com/aio-libs/yarl"
    url = "https://github.com/aio-libs/yarl"

    package_type = "python-require"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("idna/3.18")
        self.requires("multidict/6.7.1")
        self.requires("propcache/0.5.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        if not os.path.isdir(os.path.join(self.source_folder, "yarl")):
            raise ConanException("yarl package directory not found in source")

    def package(self):
        pkg_dir = os.path.join(self.package_folder, "lib", "python3.12", "site-packages", "yarl")
        os.makedirs(pkg_dir, exist_ok=True)
        src = os.path.join(self.source_folder, "yarl")
        for f in os.listdir(src):
            fpath = os.path.join(src, f)
            if os.path.isdir(fpath):
                continue
            if f.endswith((".pyx", ".pxd", ".c", ".h")):
                continue  # C/Cython sources not needed; pure-Python fallback used
            shutil.copy2(fpath, os.path.join(pkg_dir, f))
        # 附带上游测试源码（tests/），供 test_package 实际运行上游 pytest
        # 回填真实通过率（规则 4：上游测试必须实测运行，不写 N/A）。
        tests_dir = os.path.join(self.package_folder, "share", "yarl", "tests")
        src_tests = os.path.join(self.source_folder, "tests")
        if os.path.isdir(src_tests):
            shutil.copytree(src_tests, tests_dir)

    def package_info(self):
        self.cpp_info.libs = []