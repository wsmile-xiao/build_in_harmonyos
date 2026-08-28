import os
import shutil

from conan import ConanFile
from conan.tools.files import download


class DebhelperConan(ConanFile):
    name = "debhelper"
    version = "13.3.4"
    package_type = "application"
    license = "GPL-2.0"
    homepage = "https://joeyh.name/code/debhelper/"
    description = ("debhelper — Debian helper programs (pure Perl tools — "
                   "dh script + Dh_Lib modules, no compile)")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # 纯 Perl 工具集——无编译——安装 dh 脚本到 bin/ + lib/ 到 perl site-lib

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "debhelper_13.3.4.tar.xz",
                 sha256=self.conan_data["sources"]["sha256"])
        self.run("tar -xJf debhelper_13.3.4.tar.xz --no-same-owner || true")
        self.run("cp -a debhelper/. . && rm -rf debhelper")

    def build(self):
        pass

    def package(self):
        # dh 脚本（bin/）+ lib/ 的 .pm（perl site-lib）——先建 bin/ 目录
        # （shutil.copy 目标目录不存在 'No such file' 实测）
        os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "dh"),
                    os.path.join(self.package_folder, "bin", "dh"))
        os.chmod(os.path.join(self.package_folder, "bin", "dh"), 0o755)
        lib = os.path.join(self.source_folder, "lib")
        if os.path.isdir(lib):
            shutil.copytree(lib,
                            os.path.join(self.package_folder, "lib", "perl5"),
                            dirs_exist_ok=True)

    def package_info(self):
        self.cpp_info.libs = []
