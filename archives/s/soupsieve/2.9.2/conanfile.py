#!/usr/bin/env python3
"""Conan recipe for soupsieve 2.9.2 — pure Python CSS selector engine.

soupsieve is the CSS selector engine used by beautifulsoup4. Pure Python
(noarch), no C/C++ compilation. Runtime deps: none (self-contained).
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class SoupsieveConan(ConanFile):
    name = "soupsieve"
    version = "2.9.2"
    description = "A modern CSS selector implementation for BeautifulSoup"
    license = "MIT"
    homepage = "https://github.com/facelessuser/soupsieve"
    url = ""

    # Pure Python noarch: no compiler needed (same pattern as acronym/pyroute2)
    settings = "os", "arch", "compiler", "build_type"
    # 注意：主配方**不** requires beautifulsoup4——bs4 4.15.0 依赖
    # soupsieve/2.4.1（不同版本）——主配方 requires bs4 会形成依赖环
    # （soupsieve/2.9.2 → bs4 → soupsieve/2.4.1——'cycle/loop in the
    # graph' 实测）——bs4 仅 test_package 的 requires（test 的 PYTHONPATH
    # 遍历依赖——soupsieve 的 __init__.py 顶层 import bs4 由 test 提供）

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # soupsieve 2.9.2 的 __init__.py 顶层 import bs4（必需）——bs4 4.15.0
        # 依赖 soupsieve/2.4.1（不同版本）——test_package 不能 requires bs4
        # （'Conflict originates from beautifulsoup4' 实测 #6365）——
        # patch import bs4 改可选（test 用 compile/escape——无树依赖）
        _init = os.path.join(self.source_folder, "soupsieve", "__init__.py")
        _text = open(_init).read()
        if "import bs4" in _text and "except ImportError" not in _text:
            _text = _text.replace(
                "import bs4",
                "try:\n    import bs4\nexcept ImportError:\n    bs4 = None",
                1)
            open(_init, "w").write(_text)
            self.output.info("soupsieve __init__.py bs4 import made optional")
        python_exe = sys.executable
        src_dir = self.source_folder
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)

        # Build deps: setuptools + wheel
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 setuptools wheel',
        )
        # Install into staging via --prefix (no deps — soupsieve is self-contained)
        self.run(
            f'{python_exe} -m pip install --break-system-packages --no-deps '
            f'--prefix="{staging}" "{src_dir}"',
        )

    def package(self):
        # Copy staged site-packages + bin into the package folder
        # （acronym 同款模式：绝对 dst——lib/<pyver>/site-packages）
        staging = os.path.join(self.build_folder, "staging")
        py_ver = self._py_ver()
        site_dst = os.path.join(
            self.package_folder, "lib", py_ver, "site-packages"
        )
        bin_dst = os.path.join(self.package_folder, "bin")

        site_src = None
        for candidate in (
            os.path.join(staging, "lib", py_ver, "site-packages"),
            os.path.join(staging, "lib", py_ver, "dist-packages"),
            os.path.join(staging, "local", "lib", py_ver, "site-packages"),
            os.path.join(staging, "local", "lib", py_ver, "dist-packages"),
        ):
            if os.path.isdir(candidate) and os.path.isdir(
                os.path.join(candidate, "soupsieve")
            ):
                site_src = candidate
                break
        if site_src is None:
            raise Exception(
                f"soupsieve site-packages not found under staging={staging}"
            )
        copy(self, "*", src=site_src, dst=site_dst)

        for bin_src in (
            os.path.join(staging, "bin"),
            os.path.join(staging, "local", "bin"),
        ):
            if os.path.isdir(bin_src):
                copy(self, "*", src=bin_src, dst=bin_dst)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def package_info(self):
        site = os.path.join(
            self.package_folder, "lib", self._py_ver(), "site-packages"
        )
        self.output.info(f"PYTHONPATH += {site}")
        self.env_info.PYTHONPATH.append(site)
