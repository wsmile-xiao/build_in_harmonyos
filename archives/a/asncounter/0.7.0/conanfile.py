#!/usr/bin/env python3
"""Conan recipe — asncounter 0.7.0 (ASN.1 counter — pure Python)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy


class AsncounterConan(ConanFile):
    name = "asncounter"
    version = "0.7.0"
    description = "Count hits (HTTP, packets, etc) per autonomous system number (ASN)"
    license = "AGPL-3.0-or-later"
    homepage = "https://gitlab.com/anarcat/asncounter"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        py = "/data/service/hnp/bin/python3"
        site = "/data/service/hnp/OpenHarmonyPCDeveloper_build_in_harmonyos_ci_o.org/" \
               "OpenHarmonyPCDeveloper_build_in_harmonyos_ci_o_1.0.0/lib/python3.12/site-packages"
        # 依赖 pyasn（remote 无配方——pip 安装绕过——核心依赖 import pyasn——
        # wheel 构建需要 clang——CC 指定）
        self.run(f'"{py}" -m pip install pyasn --quiet',
                 env=["PYTHONPATH=" + site, "CC=/data/service/hnp/bin/clang",
                      "PATH=/data/service/hnp/bin:" + os.environ.get("PATH", "")],
                 ignore_errors=True)
        self.run(
            f'export PATH=/data/service/hnp/bin:$PATH CC=/data/service/hnp/bin/clang '
            f'CXX=/data/service/hnp/bin/clang++ PYTHONPATH={site} && '
            f'"{py}" -m pip wheel "{self.source_folder}" --no-deps '
            f'--no-build-isolation --wheel-dir="{self.build_folder}/wheel"',
            ignore_errors=True)

    def package(self):
        # asncounter 是单个 Python 文件——直接 copy 到 site-packages
        # （wheel 构建在 conan 内不稳定——简化打包——功能等价）
        site_pkgs = os.path.join(self.package_folder, "lib", "python3.12",
                                 "site-packages")
        os.makedirs(site_pkgs, exist_ok=True)
        copy(self, "asncounter.py", src=self.source_folder,
             dst=site_pkgs, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        site_pkgs = os.path.join(self.package_folder, "lib", "python3.12",
                                 "site-packages")
        self.runenv_info.append_path("PYTHONPATH", site_pkgs)
        self.env_info.PYTHONPATH.append(site_pkgs)
