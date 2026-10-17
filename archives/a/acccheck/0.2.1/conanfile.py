#!/usr/bin/env python3
"""Conan recipe — acccheck 0.2.1（Windows SMB 口令字典攻击工具）.

acccheck 是围绕 smbclient 的 Perl 包装脚本，用于针对 Windows
SMB 认证的口令字典攻击。纯 Perl 脚本，无编译需求。
构建系统：无（纯脚本工具）
平台：OHOS aarch64 / Linux / macOS
依赖：运行时依赖系统 perl 与 smbclient（非 Conan 包）
"""

import os

from conan import ConanFile
from conan.tools.files import get, copy


class AcccheckConan(ConanFile):
    name = "acccheck"
    version = "0.2.1"
    description = "Password dictionary attack tool for Windows SMB authentication"
    license = "GPL-2.0-only"
    homepage = "https://labs.portcullis.co.uk/tools/acccheck/"
    url = "https://labs.portcullis.co.uk/tools/acccheck/"
    package_type = "application"

    settings = "os", "arch"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        # 纯脚本工具：安装主脚本到 bin/，保留可执行权限
        copy(
            self,
            "acccheck.pl",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING.GPL",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.system_libs = []
        # 运行时依赖系统 perl 与 smbclient
        self.conf_info.define("user.runtime:requires", "perl, smbclient")