#!/usr/bin/env python3
"""Conan recipe for xapers 0.9.0 — Python package (setuptools).

xapers is a personal journal article management system written in Python.
It provides a CLI tool `xapers` (console_scripts entry point) and the
`xapers` Python package.

Build system: setuptools (setup.py)
Runtime dependency: xapian Python bindings (provided by the published
xapian-bindings conan package, which in turn depends on xapian-core).
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class XapersConan(ConanFile):
    name = "xapers"
    version = "0.9.0"
    description = "Personal journal article management system"
    license = "GPL-3.0+"
    homepage = "https://finestructure.net/xapers"
    url = "https://gitlab.com/wpettersson/xapers"

    # xapers is a CLI tool (console_scripts entry point), not a library
    package_type = "application"

    # L0p 门禁要求 OHOS profile 完整四项 settings（os/compiler/build_type/arch）
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # xapian-bindings 提供 xapian Python 绑定（依赖 xapian-core，已发布）；
        # poppler 提供 pdftotext（PDF 文本提取，xapers 上游 poppler-utils 依赖）；
        # xclip 提供交互式 UI 剪贴板复制功能（已发布，运行时可选）。
        self.requires("xapian-bindings/1.4.26")
        self.requires("poppler/25.12.0.2")
        self.requires("xclip/0.13.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches (e.g. version.py fix), required by G1 check
        apply_conandata_patches(self)

        python_exe = sys.executable

        # Step 1: Install Python runtime dependencies needed by xapers
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            '"pybtex" "pycurl" "urwid"',
            env="conanrun",
        )

        # Step 2: Build and install the package to the package folder
        src_dir = self.source_folder
        self.run(
            f'{python_exe} -m pip install --break-system-packages --no-deps '
            f'--prefix="{self.package_folder}" "{src_dir}"',
            env="conanrun",
        )

    def package(self):
        # Files already installed to package_folder in build() via --prefix
        pass

    def package_info(self):
        # Set up environment for consumers
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join("lib", py_ver, "site-packages")

        # Add bin to PATH
        self.cpp_info.bindirs = ["bin"]
        # Add Python lib path
        self.cpp_info.libdirs = [site_packages]

        # Set environment variables for consumers
        bin_path = os.path.join(self.package_folder, "bin")
        lib_path = os.path.join(self.package_folder, site_packages)
        self.runenv_info.define("PATH", bin_path)
        # 使用 append_path：保留 xapian-bindings 通过 runenv_info 注入的
        # PYTHONPATH（xapian 绑定 site-packages），避免 define 覆盖。
        self.runenv_info.append_path("PYTHONPATH", lib_path)
        xb = self.dependencies["xapian-bindings"].package_folder
        self.runenv_info.append_path(
            "PYTHONPATH",
            os.path.join(xb, "lib", py_ver, "site-packages"),
        )
