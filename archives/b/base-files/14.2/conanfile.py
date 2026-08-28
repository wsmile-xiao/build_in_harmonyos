import os
import shutil

from conan import ConanFile
from conan.tools.files import download


class BaseFilesConan(ConanFile):
    name = "base-files"
    version = "14.2"
    package_type = "application"
    license = "GPL-2.0"
    homepage = "https://packages.debian.org/sid/base-files"
    description = ("base-files — Debian base system configuration files "
                   "(pure config/text, no compile)")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # 纯配置/文本包——无编译——安装 etc/ 的配置文件

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "base-files_14.2.tar.xz",
                 sha256=self.conan_data["sources"]["sha256"])
        self.run("tar -xJf base-files_14.2.tar.xz --no-same-owner || true")
        self.run("cp -a base-files/. . && rm -rf base-files")

    def build(self):
        pass

    def package(self):
        # 安装 etc/ 的配置文件（debian_version/host.conf/issue 等）
        etc = os.path.join(self.source_folder, "etc")
        if os.path.isdir(etc):
            shutil.copytree(etc, os.path.join(self.package_folder, "etc"),
                            dirs_exist_ok=True)

    def package_info(self):
        self.cpp_info.libs = []
