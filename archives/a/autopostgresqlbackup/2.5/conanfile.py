import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class AutopostgresqlbackupConan(ConanFile):
    name = "autopostgresqlbackup"
    version = "2.5"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"]["autopostgresqlbackup"],
            strip_root=True)

    def build(self):
        # 纯 bash 脚本工具——无编译——复制脚本 + 配置（同 backup2l 模式）
        pass

    def package(self):
        src = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")
        confdir = os.path.join(self.package_folder, "etc")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(confdir, exist_ok=True)
        shutil.copy(os.path.join(src, "autopostgresqlbackup"),
                    os.path.join(bindir, "autopostgresqlbackup"))
        os.chmod(os.path.join(bindir, "autopostgresqlbackup"), 0o755)
        if os.path.exists(os.path.join(src, "autopostgresqlbackup.conf")):
            shutil.copy(os.path.join(src, "autopostgresqlbackup.conf"),
                        os.path.join(confdir, "autopostgresqlbackup.conf"))

    def package_info(self):
        self.cpp_info.libs = []
