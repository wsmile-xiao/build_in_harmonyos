import os
import shutil

from conan import ConanFile
from conan.tools.files import download


class DhLinktreeConan(ConanFile):
    name = "dh-linktree"
    version = "0.9"
    package_type = "application"
    license = "GPL-3.0-or-later"
    homepage = "https://salsa.debian.org/debian/dh-linktree"
    description = ("dh-linktree — debhelper plugin creating symlink trees "
                   "(pure Perl script, no compile)")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # 纯 Perl 脚本打包——零编译——运行时依赖 debhelper(Debian::Debhelper::
    # Dh_Lib) + dpkg(Dpkg::IPC 与 dpkg/dpkg-query 命令)
    requires = "debhelper/13.3.4", "dpkg/1.23.7"

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "dh-linktree_0.9.tar.xz",
                 sha256=self.conan_data["sources"]["sha256"])
        # 沙箱 get() 有 PermissionError 风险——download + 手动解压
        # （--no-same-owner 容忍所有权错误；cp -a 收拢含隐藏文件）
        self.run("tar -xJf dh-linktree_0.9.tar.xz --no-same-owner || true")
        self.run("cp -a dh-linktree/. . && rm -rf dh-linktree")

    def build(self):
        pass

    def package(self):
        # 挑文件安装（禁止整目录拷贝）：
        #   dh_linktree   → <pkg>/bin/dh_linktree (0755)
        #   linktree.pm   → <pkg>/lib/perl5/Debian/Debhelper/Sequence/linktree.pm
        #   dh_linktree.1 → <pkg>/share/man/man1/dh_linktree.1
        os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "dh_linktree"),
                    os.path.join(self.package_folder, "bin", "dh_linktree"))
        os.chmod(os.path.join(self.package_folder, "bin", "dh_linktree"), 0o755)
        seq = os.path.join(self.package_folder, "lib", "perl5",
                           "Debian", "Debhelper", "Sequence")
        os.makedirs(seq, exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "linktree.pm"),
                    os.path.join(seq, "linktree.pm"))
        man = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(man, exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "dh_linktree.1"),
                    os.path.join(man, "dh_linktree.1"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
