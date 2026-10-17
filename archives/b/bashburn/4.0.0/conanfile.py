import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class BashburnConan(ConanFile):
    name = "bashburn"
    version = "4.0.0"
    package_type = "application"
    license = "GPL-2.0"
    homepage = "https://gitlab.com/anders.linden/BashBurn"
    description = ("bashburn — CD/DVD burning shell script (pure bash, no compile)")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # 纯 shell 脚本——无编译依赖——cdrecord/cdrdao/mkisofs 是运行时依赖
    # （脚本运行时才调用——安装/构建不需要）——不 requires

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 shell 脚本——无编译——直接安装（code/ 的脚本）
        pass

    def package(self):
        # 安装 bashburn 脚本（code/BashBurn.sh + Install.sh 等）
        src = os.path.join(self.source_folder, "code")
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for f in os.listdir(src):
            if f.endswith(".sh") or f == "BashBurn.sh":
                shutil.copy2(os.path.join(src, f),
                             os.path.join(bin_dir, f))
                os.chmod(os.path.join(bin_dir, f), 0o755)
        # 主脚本 BashBurn.sh 放 bin/bashburn
        main = os.path.join(bin_dir, "BashBurn.sh")
        if os.path.isfile(main):
            os.rename(main, os.path.join(bin_dir, "bashburn"))

    def package_info(self):
        self.cpp_info.libs = []
