#!/usr/bin/env python3
"""Conan recipe for git-ftp 1.6.0 — shell script tool.

git-ftp uses Git-based FTP/FTPS/SFTP upload via a shell script.
No compilation needed — just install the script and man page.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class GitFtpConan(ConanFile):
    name = "git-ftp"
    version = "1.6.0"
    description = "Git-powered FTP/FTPS/SFTP client — shell script"
    license = "GPL-2.0-only"
    homepage = "https://git-ftp.github.io/"
    url = "https://github.com/git-ftp/git-ftp"

    package_type = "application"

    settings = "os", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass

    def package(self):
        # Install git-ftp script to bin/
        copy(self, "git-ftp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # GitHub archive tarball 文件权限固定 0644，copy() 保留源权限，
        # 需显式 chmod 755 使脚本可执行（同 gti/gws/gradle 等配方）
        os.chmod(os.path.join(self.package_folder, "bin", "git-ftp"), 0o755)
        # Install man page
        copy(self, "git-ftp.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
