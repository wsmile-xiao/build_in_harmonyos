#!/usr/bin/env python3
"""Conan recipe — adman 0.9.0（Active Directory 自动化维护工具）.

adman 是纯 Python 工具，用于 Active Directory 自动化管理
（账号/密码过期/陈旧账号扫描等）。
构建系统：无（纯 Python 脚本工具，setuptools 打包）
平台：OHOS aarch64 / Linux / macOS
依赖：运行时依赖系统 python3 与 python-ldap/dnspython/PyYAML
"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import copy, get


class AdmanConan(ConanFile):
    name = "adman"
    version = "0.9.0"
    description = "adman — Active Directory Automated Maintenance"
    license = "MIT"
    homepage = "https://gitlab.com/JonathonReinhart/adman"
    url = "https://gitlab.com/JonathonReinhart/adman"
    package_type = "application"

    settings = "os", "arch"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        # 纯 Python 工具：复制 adman/ 包到 usr/lib/python/site-packages/
        # （用 shutil.copytree 确保整个包目录被复制）
        pkg_dst = os.path.join(self.package_folder, "usr", "lib", "python", "site-packages", "adman")
        shutil.copytree(os.path.join(self.source_folder, "adman"), pkg_dst)
        # 生成 bin/adman 启动脚本（python3 -m adman，PYTHONPATH 指向包内 site-packages）
        launcher = os.path.join(self.package_folder, "usr", "bin", "adman")
        os.makedirs(os.path.dirname(launcher), exist_ok=True)
        with open(launcher, "w") as f:
            f.write(
                "#!/bin/sh\n"
                "DIR=$(dirname \"$(readlink -f \"$0\")\")/../lib/python/site-packages\n"
                "PYTHONPATH=\"$DIR${PYTHONPATH:+:$PYTHONPATH}\" "
                "exec python3 -m adman \"$@\"\n"
            )
        os.chmod(launcher, 0o755)
        # 许可证
        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["usr/bin"]
        self.cpp_info.libdirs = []