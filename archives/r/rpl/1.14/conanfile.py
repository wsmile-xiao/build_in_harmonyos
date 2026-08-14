#!/usr/bin/env python3
"""Conan recipe — rpl 1.14（文本批量替换工具，纯 Python）

rpl 是纯 Python 命令行工具（单脚本 rpl），运行时依赖 chardet。
上游 setuptools 构建（setup.cfg 的 build_manpages 要求 rpl.1，而 Debian
orig 包不含该 man page，wheel 构建失败），故绕开 setuptools：
- 直接复制 rpl 脚本到 bin/
- pip 只安装运行时依赖 chardet 到 site-packages（PYTHONPATH 注入）
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches


class RplConan(ConanFile):
    name = "rpl"
    version = "1.14"
    description = "rpl — Replace strings in files（文本批量替换工具）"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/rrthomas/rpl"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    # OHOS profile 要求四项 settings（L0p 门禁）；纯 Python 但需与 profile 对齐
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def build(self):
        python_exe = sys.executable
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)
        # 仅安装运行时依赖 chardet 到 staging（不装 rpl 本体——绕开 rpl.1 问题）
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 --prefix="{staging}" chardet',
        )

    def package(self):
        src = self.source_folder
        staging = os.path.join(self.build_folder, "staging")
        py_ver = self._py_ver()
        site_dst = os.path.join(
            self.package_folder, "lib", py_ver, "site-packages"
        )
        bin_dst = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dst, exist_ok=True)

        # rpl 单脚本直接复制到 bin/
        copy(self, "rpl", src=src, dst=bin_dst, keep_path=False)

        # chardet site-packages
        site_src = None
        for candidate in (
            os.path.join(staging, "lib", py_ver, "site-packages"),
            os.path.join(staging, "lib", py_ver, "dist-packages"),
            os.path.join(staging, "local", "lib", py_ver, "site-packages"),
            os.path.join(staging, "local", "lib", py_ver, "dist-packages"),
        ):
            if os.path.isdir(candidate):
                site_src = candidate
                break
        if site_src is None:
            # pip 可能判定 chardet 已满足而跳过 --prefix 安装 → 从本机 sys.path 定位
            import chardet as _chardet
            chardet_dir = os.path.dirname(os.path.abspath(_chardet.__file__))
            site_src = os.path.dirname(chardet_dir)
            self.output.info(f"chardet from local site-packages: {site_src}")
        copy(self, "*", src=site_src, dst=site_dst)

        for lic_name in ("COPYING", "LICENSE", "LICENSE.txt", "LICENSE.md"):
            lic = os.path.join(src, lic_name)
            if os.path.isfile(lic):
                copy(self, lic_name, src=src,
                     dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

        site_packages = os.path.join(
            self.package_folder, "lib", self._py_ver(), "site-packages"
        )
        self.runenv_info.append_path("PYTHONPATH", site_packages)
        self.buildenv_info.append_path("PYTHONPATH", site_packages)
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)
