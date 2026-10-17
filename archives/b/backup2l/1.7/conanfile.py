#!/usr/bin/env python3
"""Conan recipe for backup2l 1.7 on HarmonyOS PC.

backup2l is a low-maintenance backup/restore tool — a single bash
script (no compilation). Install via install-sh: the backup2l script
goes to bin/, first-time.conf to etc/backup2l/, man page to share/man.

Runtime deps are system shell tools (bash, tar, gzip, gunzip, sed,
awk, mount, umount, date, find, grep) — all provided by OHOS base.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get


class Backup2lConan(ConanFile):
    name = "backup2l"
    version = "1.7"
    package_type = "application"
    license = "GPL-2.0"
    homepage = "https://github.com/gkiefer/backup2l"
    url = "https://github.com/gkiefer/backup2l"
    description = "Low-maintenance backup/restore tool (shell script)"
    settings = "os", "arch", "compiler", "build_type"

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)

    def build(self):
        # 纯 shell 脚本——无编译（install-sh 在 package() 里做安装布局）
        pass

    def package(self):
        copy(self, "backup2l", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "backup2l.8", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "first-time.conf", src=self.source_folder,
             dst=os.path.join(self.package_folder, "etc", "backup2l"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.conf_info.define("user.backup2l:exe", os.path.join(
            self.package_folder, "bin", "backup2l"))
